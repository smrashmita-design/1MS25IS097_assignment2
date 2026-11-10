"""The ReAct execution loop.

This module implements the actual agent cycle:

    user query
        -> model decides on an action
        -> tool executes a real search
        -> observations are returned to the model
        -> the model evaluates and either acts again or answers
        -> final answer

Every stage emits an :class:`AgentEvent` so the frontend can render a live
execution timeline while the run is still in progress.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from google.genai import types

from app.agent.events import EventFactory
from app.agent.prompts import build_system_prompt
from app.config import Settings, get_settings
from app.llm.client import LLMClient, LLMError
from app.schemas.events import AgentEvent, AgentEventType
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class RunOutcome:
    """Everything the controller needs after a run finishes."""

    final_text: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    tool_calls: int = 0
    duration_ms: int = 0
    cancelled: bool = False
    error: str | None = None


class ReActLoop:
    """Drives the model/tool/observation cycle with strict iteration limits."""

    def __init__(
        self,
        llm: LLMClient,
        registry: ToolRegistry,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.settings = settings or get_settings()
        self.system_prompt = build_system_prompt(max_iterations=self.settings.max_agent_iterations)

    # ---------------------------------------------------------------- run --
    async def run(
        self,
        contents: Sequence[types.Content],
        *,
        factory: EventFactory,
        outcome: RunOutcome | None = None,
        max_iterations: int | None = None,
        should_stop: Callable[[], bool] | None = None,
        on_observation: Callable[[ToolResult, dict[str, Any]], None] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Execute the ReAct loop, yielding timeline events as they happen."""
        should_stop = should_stop or (lambda: False)
        history: list[types.Content] = list(contents)
        tools = self.registry.declarations()
        outcome = outcome if outcome is not None else RunOutcome()
        budget = max(1, min(int(max_iterations or self.settings.max_agent_iterations), 12))
        started = time.perf_counter()

        for iteration in range(1, budget + 1):
            if should_stop():
                outcome.cancelled = True
                yield factory.build(
                    AgentEventType.AGENT_CANCELLED,
                    title="Run stopped",
                    detail="Execution was cancelled before the agent produced an answer.",
                    data={"iterations": iteration - 1},
                )
                break

            outcome.iterations = iteration
            yield factory.build(
                AgentEventType.PLANNING,
                title=f"Planning · iteration {iteration}",
                detail=(
                    "Asking Gemini which tool to call and what to look up."
                    if iteration == 1
                    else "Reviewing the latest observations and deciding the next action."
                ),
                data={"iteration": iteration, "max_iterations": budget},
            )

            text_parts: list[str] = []
            function_calls: list[Any] = []
            model_parts: list[Any] = []
            turn_error: str | None = None

            try:
                async for turn in self.llm.stream_turn(
                    history,
                    tools=tools,
                    system_instruction=self.system_prompt,
                ):
                    if should_stop():
                        outcome.cancelled = True
                        break

                    if turn.text:
                        text_parts.append(turn.text)
                        yield factory.build(
                            AgentEventType.TOKEN,
                            title="Streaming response",
                            detail=None,
                            data={"text": turn.text},
                        )

                    if turn.function_calls:
                        function_calls.extend(turn.function_calls)
                    if turn.parts:
                        model_parts = list(turn.parts)
            except asyncio.CancelledError:
                outcome.cancelled = True
                raise
            except LLMError as exc:
                turn_error = exc.message
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected failure during the ReAct turn")
                turn_error = f"{type(exc).__name__}: {exc}"[:400]

            if outcome.cancelled:
                yield factory.build(
                    AgentEventType.AGENT_CANCELLED,
                    title="Run stopped",
                    detail="Execution was cancelled by the user.",
                    data={"iterations": iteration - 1},
                )
                break

            if turn_error:
                yield factory.build(
                    AgentEventType.AGENT_ERROR,
                    title="Model error",
                    detail=turn_error,
                    data={"code": "llm_error", "iteration": iteration},
                )
                outcome.error = turn_error
                break

            narration = "".join(text_parts).strip()

            # ---------------------------------------------------------- act --
            if function_calls:
                if narration:
                    yield factory.build(
                        AgentEventType.PLANNING,
                        title="Agent plan",
                        detail=narration[:600],
                        data={"iteration": iteration, "narration": True},
                    )

                # Replay the model's own parts so that the ``thought_signature``
                # required by Gemini 3.x models survives the round-trip.
                if not model_parts:
                    model_parts = [
                        types.Part.from_function_call(name=call.name, args=call.args)
                        for call in function_calls
                    ]
                history.append(types.Content(role="model", parts=model_parts))

                response_parts: list[types.Part] = []
                for call in function_calls:
                    outcome.tool_calls += 1
                    yield factory.build(
                        AgentEventType.TOOL_SELECTED,
                        title=f"Tool selected · {call.name}",
                        detail=_describe_args(call.args),
                        data={
                            "tool": call.name,
                            "args": call.args,
                            "iteration": iteration,
                            "tool_call_id": call.id,
                        },
                    )
                    yield factory.build(
                        AgentEventType.TOOL_CALL,
                        title=f"Calling {call.name}",
                        detail=_describe_args(call.args),
                        data={
                            "tool": call.name,
                            "args": call.args,
                            "iteration": iteration,
                            "tool_call_id": call.id,
                        },
                    )

                    spec = self.registry.get(call.name)
                    yield factory.build(
                        AgentEventType.TOOL_STARTED,
                        title=f"Executing {call.name}",
                        detail=spec.label if spec else "Running the registered tool.",
                        data={
                            "tool": call.name,
                            "args": call.args,
                            "iteration": iteration,
                            "tool_call_id": call.id,
                        },
                    )

                    result = await self.registry.execute(call.name, call.args)

                    if should_stop():
                        outcome.cancelled = True
                        break

                    payload = result.to_model_payload()
                    results = payload.get("results") or []

                    yield factory.build(
                        AgentEventType.TOOL_RESULT,
                        title=(
                            f"{len(results)} results returned"
                            if result.ok
                            else "Tool execution failed"
                        ),
                        detail=result.display or result.error,
                        data={
                            "tool": call.name,
                            "ok": result.ok,
                            "duration_ms": result.duration_ms,
                            "result_count": len(results),
                            "results": results,
                            "error": result.error,
                            "iteration": iteration,
                            "tool_call_id": call.id,
                        },
                    )

                    yield factory.build(
                        AgentEventType.OBSERVATION,
                        title="Observation recorded",
                        detail=_summarise_observation(payload, result),
                        data={
                            "tool": call.name,
                            "ok": result.ok,
                            "result_count": len(results),
                            "results": results,
                            "iteration": iteration,
                            "tool_call_id": call.id,
                        },
                    )

                    if on_observation is not None:
                        on_observation(result, payload)

                    response_parts.append(
                        types.Part.from_function_response(name=call.name, response=payload)
                    )

                if outcome.cancelled:
                    yield factory.build(
                        AgentEventType.AGENT_CANCELLED,
                        title="Run stopped",
                        detail="Execution was cancelled by the user.",
                        data={"iterations": iteration},
                    )
                    break

                history.append(types.Content(role="user", parts=response_parts))
                continue

            # ------------------------------------------------------- answer --
            final_text = narration.strip()
            outcome.final_text = final_text
            yield factory.build(
                AgentEventType.FINAL_ANSWER,
                title="Final response generated",
                detail=None,
                data={"content": final_text, "iteration": iteration},
            )
            break
        else:
            # The iteration budget was exhausted before the model produced an answer.
            fallback = (
                "I reached the maximum number of research iterations for this question "
                f"({budget}) before I could assemble a complete "
                "answer. Here is what I gathered so far:\n\n"
                + (outcome.final_text or "No usable observations were returned.")
            )
            outcome.final_text = fallback
            yield factory.build(
                AgentEventType.FINAL_ANSWER,
                title="Iteration limit reached",
                detail=(
                    f"Stopped after {budget} iterations and "
                    "returned a partial answer."
                ),
                data={"content": fallback, "iteration": budget},
            )

        outcome.duration_ms = int((time.perf_counter() - started) * 1000)


def _describe_args(args: dict[str, Any]) -> str:
    """Human friendly one-liner describing a tool call's arguments."""
    if not args:
        return "No arguments"
    query = args.get("query")
    if isinstance(query, str) and query:
        return f"query: “{query}”"
    return ", ".join(f"{key}: {value}" for key, value in args.items() if value is not None)


def _summarise_observation(payload: dict[str, Any], result: ToolResult) -> str:
    """Short, factual summary of what the tool returned."""
    if not result.ok:
        return result.error or "The tool reported a failure."
    results = payload.get("results") or []
    if not results:
        return "No results were returned."
    domains: list[str] = []
    for item in results:
        domain = item.get("domain") or item.get("source")
        if domain and domain not in domains:
            domains.append(domain)
    preview = ", ".join(domains[:4])
    suffix = f" Sources: {preview}." if preview else ""
    return f"Read {len(results)} search results.{suffix}"
