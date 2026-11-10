"""Tests for the ReAct execution loop using a mocked model."""

from __future__ import annotations

from app.agent.events import EventFactory
from app.agent.loop import ReActLoop, RunOutcome
from app.llm.client import ToolCall
from app.schemas.events import AgentEventType
from app.tools.registry import ToolRegistry
from app.tools.search_tool import build_search_tool
from tests.conftest import FakeLLM, FakeSearchProvider, make_results


def build_loop(script, provider, settings) -> ReActLoop:
    registry = ToolRegistry()
    spec, validator = build_search_tool(provider, settings)
    registry.register(spec, validator)
    llm = FakeLLM(script)
    return ReActLoop(llm, registry, settings)


async def collect(loop: ReActLoop, contents):
    factory = EventFactory()
    events = []
    async for event in loop.run(contents, factory=factory, outcome=RunOutcome()):
        events.append(event)
    return events


class TestSingleIteration:
    async def test_model_can_answer_without_using_a_tool(self, settings) -> None:
        loop = build_loop(["The capital of France is Paris."], FakeSearchProvider(), settings)
        events = await collect(loop, [])
        types = [event.type for event in events]
        assert AgentEventType.AGENT_STARTED not in types  # the loop does not emit it
        assert AgentEventType.FINAL_ANSWER in types
        assert AgentEventType.TOOL_CALL not in types
        final = next(e for e in events if e.type is AgentEventType.FINAL_ANSWER)
        assert "Paris" in final.data["content"]


class TestToolCalling:
    async def test_tool_call_is_executed_and_observed(self, settings) -> None:
        script = [
            [ToolCall(id="1", name="web_search", args={"query": "nexus agent"})],
            "Here is what I found.",
        ]
        provider = FakeSearchProvider(make_results(2))
        loop = build_loop(script, provider, settings)
        events = await collect(loop, [])

        types = [event.type for event in events]
        assert AgentEventType.TOOL_SELECTED in types
        assert AgentEventType.TOOL_CALL in types
        assert AgentEventType.TOOL_STARTED in types
        assert AgentEventType.TOOL_RESULT in types
        assert AgentEventType.OBSERVATION in types
        assert AgentEventType.FINAL_ANSWER in types

        tool_result = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)
        assert tool_result.data["ok"] is True
        assert tool_result.data["result_count"] == 2
        assert provider.queries == ["nexus agent"]

    async def test_observation_contains_real_results(self, settings) -> None:
        script = [
            [ToolCall(id="1", name="web_search", args={"query": "nexus"})],
            "Done.",
        ]
        provider = FakeSearchProvider(make_results(2))
        loop = build_loop(script, provider, settings)
        events = await collect(loop, [])
        observation = next(e for e in events if e.type is AgentEventType.OBSERVATION)
        urls = [r["url"] for r in observation.data["results"]]
        assert "https://example.com/article-1" in urls

    async def test_tool_arguments_are_validated(self, settings) -> None:
        script = [
            [ToolCall(id="1", name="web_search", args={"max_results": 2})],
            "Recovered.",
        ]
        provider = FakeSearchProvider(make_results(1))
        loop = build_loop(script, provider, settings)
        events = await collect(loop, [])
        tool_result = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)
        assert tool_result.data["ok"] is False
        assert provider.queries == []  # the invalid call never reached the provider


class TestMultipleIterations:
    async def test_agent_can_search_twice(self, settings) -> None:
        script = [
            [ToolCall(id="1", name="web_search", args={"query": "first"})],
            [ToolCall(id="2", name="web_search", args={"query": "second"})],
            "Final synthesis.",
        ]
        provider = FakeSearchProvider(make_results(1))
        loop = build_loop(script, provider, settings)
        events = await collect(loop, [])

        tool_calls = [e for e in events if e.type is AgentEventType.TOOL_CALL]
        assert len(tool_calls) == 2
        assert provider.queries == ["first", "second"]

    async def test_planning_event_per_iteration(self, settings) -> None:
        script = [
            [ToolCall(id="1", name="web_search", args={"query": "first"})],
            [ToolCall(id="2", name="web_search", args={"query": "second"})],
            "Done.",
        ]
        loop = build_loop(script, FakeSearchProvider(make_results(1)), settings)
        events = await collect(loop, [])
        planning = [e for e in events if e.type is AgentEventType.PLANNING]
        assert len(planning) == 3  # one per iteration, including the final one


class TestIterationLimit:
    async def test_loop_stops_at_the_iteration_limit(self, settings) -> None:
        settings.max_agent_iterations = 2
        script = [
            [ToolCall(id="1", name="web_search", args={"query": "one"})],
            [ToolCall(id="2", name="web_search", args={"query": "two"})],
            [ToolCall(id="3", name="web_search", args={"query": "three"})],
        ]
        provider = FakeSearchProvider(make_results(1))
        loop = build_loop(script, provider, settings)
        events = await collect(loop, [])

        tool_calls = [e for e in events if e.type is AgentEventType.TOOL_CALL]
        assert len(tool_calls) == 2
        final = next(e for e in events if e.type is AgentEventType.FINAL_ANSWER)
        assert "maximum number of research iterations" in final.data["content"]

    async def test_run_outcome_tracks_iterations_and_calls(self, settings) -> None:
        settings.max_agent_iterations = 3
        script = [
            [ToolCall(id="1", name="web_search", args={"query": "one"})],
            "Answer.",
        ]
        outcome = RunOutcome()
        loop = build_loop(script, FakeSearchProvider(make_results(1)), settings)
        factory = EventFactory()
        async for _ in loop.run([], factory=factory, outcome=outcome):
            pass
        assert outcome.tool_calls == 1
        assert outcome.iterations == 2
        assert "Answer." in outcome.final_text


class TestSearchFailure:
    async def test_search_failure_is_observed_and_reported(self, settings) -> None:
        from app.search.base import SearchProviderError

        script = [
            [ToolCall(id="1", name="web_search", args={"query": "boom"})],
            "I could not find anything.",
        ]
        provider = FakeSearchProvider(error=SearchProviderError("provider offline"))
        loop = build_loop(script, provider, settings)
        events = await collect(loop, [])

        tool_result = next(e for e in events if e.type is AgentEventType.TOOL_RESULT)
        assert tool_result.data["ok"] is False
        assert "provider offline" in tool_result.data["error"]
        assert AgentEventType.FINAL_ANSWER in [e.type for e in events]


class TestCancellation:
    async def test_stop_signal_ends_the_run(self, settings) -> None:
        script = [
            [ToolCall(id="1", name="web_search", args={"query": "one"})],
            "should not be reached",
        ]
        loop = build_loop(script, FakeSearchProvider(make_results(1)), settings)
        factory = EventFactory()
        events = []
        async for event in loop.run(
            [], factory=factory, should_stop=lambda: True
        ):
            events.append(event)
        assert events[0].type is AgentEventType.AGENT_CANCELLED
