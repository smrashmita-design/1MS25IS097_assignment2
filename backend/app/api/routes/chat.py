"""The streaming chat endpoint (Server-Sent Events)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.agent.controller import AgentController
from app.api.deps import get_controller
from app.schemas.chat import ChatRequest, StopRequest, StopResponse
from app.schemas.events import AgentEvent, AgentEventType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
    "Content-Type": "text/event-stream; charset=utf-8",
}


async def _pump(events: AsyncIterator[AgentEvent], heartbeat: float = 12.0) -> AsyncIterator[str]:
    """Convert agent events into SSE frames, emitting heartbeats when idle."""
    pending: asyncio.Task | None = None
    try:
        while True:
            if pending is None:
                pending = asyncio.ensure_future(events.__anext__())
            done, _ = await asyncio.wait({pending}, timeout=heartbeat)
            if not done:
                yield ": heartbeat\n\n"
                continue
            try:
                event = pending.result()
            except StopAsyncIteration:
                return
            finally:
                pending = None
            yield event.to_sse()
    finally:
        if pending is not None and not pending.done():
            pending.cancel()


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    controller: AgentController = Depends(get_controller),
) -> StreamingResponse:
    """Run the ReAct agent and stream its execution timeline over SSE."""
    run_id = payload.run_id or uuid.uuid4().hex

    async def generator() -> AsyncIterator[str]:
        yield "retry: 3000\n\n"
        try:
            async for event in controller.stream_run(
                message=payload.message,
                conversation_id=payload.conversation_id,
                run_id=run_id,
                max_iterations=payload.max_iterations,
                save_search=payload.save_search,
            ):
                if await request.is_disconnected():
                    logger.info("Client disconnected; stopping run %s", run_id)
                    controller.request_stop(run_id)
                    break
                yield event.to_sse()
        except asyncio.CancelledError:  # pragma: no cover - client abort
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled error while streaming the agent run")
            failure = AgentEvent(
                type=AgentEventType.AGENT_ERROR,
                title="Backend error",
                detail=str(exc)[:400] or "The agent run failed unexpectedly.",
                data={"code": "internal_error"},
            )
            yield failure.to_sse()
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/chat/stop", response_model=StopResponse)
async def chat_stop(
    payload: StopRequest,
    controller: AgentController = Depends(get_controller),
) -> StopResponse:
    """Cancel a running agent execution."""
    stopped = controller.request_stop(payload.run_id)
    return StopResponse(
        run_id=payload.run_id,
        stopped=stopped,
        detail=(
            "Stop signal delivered."
            if stopped
            else "No active run matched that id — it may have already finished."
        ),
    )
