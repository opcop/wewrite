"""任务调度：全局并发上限 + 每用户在途上限 + FIFO 排队 + 执行编排。

单进程内存版（P1）。编排：build_workspace → runner.run → 收集产物 → 清理。
状态外部化 / 多机分发属 P2。
"""
from __future__ import annotations

import asyncio

from .config import Settings


class Scheduler:
    def __init__(self, settings: Settings, *, runner=None) -> None:
        self._settings = settings
        self._sem = asyncio.Semaphore(max(1, settings.max_concurrent_jobs))
        self._user_inflight: dict[str, int] = {}
        self._user_lock = asyncio.Lock()
        self._waiting: list[str] = []
        self._tasks: set[asyncio.Task] = set()
        self._runner = runner  # 注入用于测试；None → get_runner(settings)

    def submit(self, job) -> None:
        task = asyncio.create_task(self._run(job))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, job) -> None:
        await self._acquire_user_slot(job)
        try:
            if self._sem.locked():
                self._waiting.append(job.id)
                job.emit({"type": "queued", "position": len(self._waiting)})
                try:
                    await self._sem.acquire()
                finally:
                    if job.id in self._waiting:
                        self._waiting.remove(job.id)
            else:
                await self._sem.acquire()
            try:
                await self._execute(job)
            except Exception:  # noqa: BLE001 – slot must be released; caller handles via job.status
                pass
            finally:
                self._sem.release()
        finally:
            await self._release_user_slot(job)

    async def _acquire_user_slot(self, job) -> None:
        cap = self._settings.max_per_user_jobs
        announced = False
        while True:
            async with self._user_lock:
                if self._user_inflight.get(job.user_id, 0) < cap:
                    self._user_inflight[job.user_id] = self._user_inflight.get(job.user_id, 0) + 1
                    return
            if not announced:
                job.emit({"type": "queued", "position": len(self._waiting) + 1})
                announced = True
            await asyncio.sleep(0.05)

    async def _release_user_slot(self, job) -> None:
        async with self._user_lock:
            n = self._user_inflight.get(job.user_id, 0) - 1
            if n <= 0:
                self._user_inflight.pop(job.user_id, None)
            else:
                self._user_inflight[job.user_id] = n

    async def _execute(self, job) -> None:
        from . import agent_runner as ar
        from .job_spec import JobSpec
        from .platforms import get_profile
        from .runners.base import get_runner
        from .store import STORE
        from .workspace import agent_env, build_workspace, cleanup_workspace

        settings = self._settings
        account = STORE.account(job.user_id)
        theme = job.theme or account.theme
        persona = job.persona or account.writing_persona

        # 捕获 result_meta 里的 completion（direct/container 两种来源都经此回调）
        captured: dict = {}

        def emit(ev: dict) -> None:
            if ev.get("type") == "result_meta" and ev.get("completion"):
                captured["completion"] = ev["completion"]
            job.emit(ev)

        job.status = "running"
        job.emit({"type": "status", "status": "running"})

        ws = None
        try:
            if job.kind == "distribute":
                profiles = [p for p in (get_profile(pid) for pid in job.target_platforms) if p]
                if not profiles:
                    raise RuntimeError("无有效目标平台")
                ws = build_workspace(settings, account, theme=theme, persona=persona)
                (ws / "output").mkdir(exist_ok=True)
                (ws / "output" / "source.md").write_text(job.source_markdown, encoding="utf-8")
                ar._seed_source_images(job, ws)
                spec = JobSpec(kind="distribute", prompt=job.prompt, theme=theme, persona=persona,
                               source_markdown=job.source_markdown, target_platforms=list(job.target_platforms))
            else:
                profiles = []
                publish = job.publish_draft and account.wechat_bound
                if job.publish_draft and not account.wechat_bound:
                    job.emit({"type": "notice",
                              "text": "未绑定微信公众号，已自动降级为仅本地生成（不推送草稿箱）。"})
                ws = build_workspace(settings, account, theme=theme, persona=persona)
                spec = JobSpec(kind="generate", prompt=job.prompt, theme=theme, persona=persona,
                               interactive=job.interactive, publish=publish)

            job.emit({"type": "log", "text": f"工作区已就绪：{ws.name}"})
            env = agent_env(settings, account, theme=theme)
            runner = self._runner or get_runner(settings)
            await runner.run(settings=settings, spec=spec, profiles=profiles, ws=ws, env=env, emit=emit)

            job.completion = captured.get("completion") or "DONE"
            if job.kind == "distribute":
                ar._persist_images(job, ws / "output")
                job.platform_versions = await asyncio.to_thread(
                    ar._collect_platform_versions, job, ws, job.source_markdown, profiles)
                job.status = "done"
                job.emit({"type": "status", "status": "done",
                          "versions": [{"platform": v["platform"], "status": v["status"],
                                        "passed": v.get("passed")} for v in job.platform_versions]})
            else:
                ar._collect_outputs(job, ws, theme=theme)
                job.status = "done"
                job.emit({"type": "status", "status": "done", "completion": job.completion})
        except Exception as exc:  # noqa: BLE001 - 把任意失败回传前端
            job.status = "error"
            job.error = f"{type(exc).__name__}: {exc}"
            job.emit({"type": "status", "status": "error", "error": job.error})
        finally:
            cleanup_workspace(ws)
            job.finish()
