"""Event construction helpers for the agent execution timeline."""

from __future__ import annotations

from typing import Any

from app.schemas.events import AgentEvent, AgentEventType


class EventFactory:
    """Creates monotonically numbered :class:`AgentEvent` records.

    The step counter drives the vertical timeline in the UI: every stage of the
    ReAct cycle occupies exactly one row.
    """

    def __init__(self, start: int = 0) -> None:
        self._step = start

    @property
    def step(self) -> int:
        return self._step

    def build(
        self,
        event_type: AgentEventType,
        *,
        title: str,
        detail: str | None = None,
        data: dict[str, Any] | None = None,
        step: int | None = None,
    ) -> AgentEvent:
        if step is None:
            self._step += 1
            step = self._step
        return AgentEvent(
            type=event_type,
            step=step,
            title=title,
            detail=detail,
            data=data or {},
        )
