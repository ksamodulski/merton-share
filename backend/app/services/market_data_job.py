"""Background job runner for the market-data fetch.

The expensive Claude call (web search + reasoning, minutes long) used to run
*inside* the streaming request, so any client disconnect — refresh, tab close,
navigation — cancelled it. This module runs the fetch as a detached asyncio
task that is independent of any HTTP connection: clients merely *view* its
progress. A refresh re-attaches and replays progress; the job keeps running and
persists its result regardless of who is watching.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator

from app.services import market_data_cache as cache
from app.services.claude_service import get_claude_service


@dataclass
class MarketDataJob:
    id: str
    started_at: datetime
    status: str = "running"  # running | done | error | cancelled
    events: list[dict] = field(default_factory=list)  # status events, each with an "at"
    raw_result: dict | None = None
    error: str | None = None
    task: asyncio.Task | None = None
    cond: asyncio.Condition = field(default_factory=asyncio.Condition)

    @property
    def elapsed_seconds(self) -> int:
        end = self.started_at if self.status == "running" else datetime.utcnow()
        # For a finished job we don't track end-time separately; elapsed is only
        # meaningful while running, so report wall time since start either way.
        return int((datetime.utcnow() - self.started_at).total_seconds())


_current: MarketDataJob | None = None


def current() -> MarketDataJob | None:
    return _current


def is_running() -> bool:
    return _current is not None and _current.status == "running"


async def _emit(job: MarketDataJob, event: dict) -> None:
    event = {**event, "at": datetime.now().strftime("%H:%M:%S")}
    async with job.cond:
        job.events.append(event)
        job.cond.notify_all()


async def _set_status(job: MarketDataJob, status: str) -> None:
    async with job.cond:
        job.status = status
        job.cond.notify_all()


async def _run(job: MarketDataJob) -> None:
    claude = get_claude_service()
    try:
        async for ev in claude.gather_market_data_streaming():
            etype = ev.get("type")
            if etype == "result":
                job.raw_result = ev["data"]
            elif etype == "error":
                job.error = ev.get("detail", "Fetch failed")
                await _set_status(job, "error")
                return
            else:
                await _emit(job, ev)

        if job.raw_result is None:
            job.error = "No data returned from Claude"
            await _set_status(job, "error")
            return

        # Persist the raw result so it survives a restart and can be re-blended
        # with any user's views without paying for another fetch.
        cache.set(job.raw_result, datetime.utcnow())
        await _set_status(job, "done")
    except asyncio.CancelledError:
        await _set_status(job, "cancelled")
        raise
    except Exception as e:  # noqa: BLE001 — surfaced via job.error
        job.error = str(e)
        await _set_status(job, "error")


def start() -> MarketDataJob:
    """Start a new background fetch, or return the one already running.

    Idempotent while a job is in flight, so a second client (or a double click)
    attaches to the existing run instead of triggering another paid fetch.
    """
    global _current
    if _current is not None and _current.status == "running":
        return _current
    job = MarketDataJob(id=uuid.uuid4().hex[:8], started_at=datetime.utcnow())
    job.task = asyncio.create_task(_run(job))
    _current = job
    return job


async def cancel() -> bool:
    """Cancel the running job, if any. Returns True if something was cancelled."""
    job = _current
    if job is None or job.status != "running" or job.task is None:
        return False
    job.task.cancel()
    try:
        await job.task
    except asyncio.CancelledError:
        pass
    return True


async def stream_events(job: MarketDataJob, from_index: int = 0) -> AsyncIterator[dict]:
    """Yield the job's status events (replaying any already buffered) until it
    finishes. Cancelling this generator (client disconnect) does NOT affect the
    underlying job."""
    i = from_index
    while True:
        async with job.cond:
            await job.cond.wait_for(
                lambda: len(job.events) > i or job.status != "running"
            )
            new = job.events[i:]
            i = len(job.events)
            finished = job.status != "running"
        for ev in new:
            yield ev
        if finished and i >= len(job.events):
            return
