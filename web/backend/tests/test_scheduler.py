import asyncio
from app.config import Settings
from app.scheduler import Scheduler

class FakeJob:
    def __init__(self, jid, user="u"):
        self.id = jid; self.user_id = user
        self.events = []
    def emit(self, ev): self.events.append(ev)

def _run(coro): return asyncio.run(coro)

def test_global_cap_not_exceeded(monkeypatch):
    monkeypatch.setenv("WEWRITE_MAX_CONCURRENT_JOBS", "2")
    monkeypatch.setenv("WEWRITE_MAX_PER_USER_JOBS", "10")
    sched = Scheduler(Settings())
    peak = {"now": 0, "max": 0}
    async def fake_execute(job):
        peak["now"] += 1; peak["max"] = max(peak["max"], peak["now"])
        await asyncio.sleep(0.05)
        peak["now"] -= 1
    sched._execute = fake_execute  # type: ignore

    async def go():
        jobs = [FakeJob(f"j{i}", user=f"u{i}") for i in range(6)]
        for j in jobs: sched.submit(j)
        await asyncio.gather(*sched._tasks)
    _run(go())
    assert peak["max"] <= 2

def test_per_user_cap(monkeypatch):
    monkeypatch.setenv("WEWRITE_MAX_CONCURRENT_JOBS", "10")
    monkeypatch.setenv("WEWRITE_MAX_PER_USER_JOBS", "1")
    sched = Scheduler(Settings())
    peak = {"now": 0, "max": 0}
    async def fake_execute(job):
        peak["now"] += 1; peak["max"] = max(peak["max"], peak["now"])
        await asyncio.sleep(0.05)
        peak["now"] -= 1
    sched._execute = fake_execute  # type: ignore
    async def go():
        jobs = [FakeJob(f"j{i}", user="same") for i in range(4)]
        for j in jobs: sched.submit(j)
        await asyncio.gather(*sched._tasks)
    _run(go())
    assert peak["max"] == 1

def test_slot_released_on_error(monkeypatch):
    monkeypatch.setenv("WEWRITE_MAX_CONCURRENT_JOBS", "1")
    monkeypatch.setenv("WEWRITE_MAX_PER_USER_JOBS", "1")
    sched = Scheduler(Settings())
    calls = {"n": 0}
    async def boom(job):
        calls["n"] += 1
        raise RuntimeError("x")
    sched._execute = boom  # type: ignore
    async def go():
        for j in [FakeJob("a"), FakeJob("b")]:
            sched.submit(j)
        await asyncio.gather(*sched._tasks)
    _run(go())
    assert calls["n"] == 2
