import shutil
import subprocess
import asyncio
import json
from pathlib import Path
import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None
    or subprocess.run(["docker", "info"], capture_output=True).returncode != 0,
    reason="docker daemon not available",
)

FAKE_DOCKERFILE = """
FROM python:3.11-slim
COPY entry.py /entry.py
ENTRYPOINT ["python", "/entry.py"]
"""
FAKE_ENTRY = '''
import json, sys, pathlib
print(json.dumps({"type":"assistant_text","text":"[1/8] fake"}), flush=True)
print(json.dumps({"type":"result_meta","completion":"DONE","num_turns":1}), flush=True)
out = pathlib.Path("/workspace/output"); out.mkdir(exist_ok=True)
(out/"article.md").write_text("# 假成稿\\n\\n内容。", encoding="utf-8")
'''

def test_container_runner_streams_and_collects(tmp_path, monkeypatch):
    ctx = tmp_path / "ctx"; ctx.mkdir()
    (ctx / "Dockerfile").write_text(FAKE_DOCKERFILE)
    (ctx / "entry.py").write_text(FAKE_ENTRY)
    assert subprocess.run(["docker", "build", "-t", "wewrite-job-fake", str(ctx)],
                          capture_output=True).returncode == 0

    monkeypatch.setenv("WEWRITE_JOB_IMAGE", "wewrite-job-fake")
    monkeypatch.setenv("WEWRITE_JOB_NETWORK", "bridge")
    from app.config import Settings
    from app.runners.container import ContainerRunner
    from app.job_spec import JobSpec

    ws = tmp_path / "ws"; ws.mkdir()
    events = []
    spec = JobSpec(kind="generate", prompt="x")
    r = ContainerRunner(Settings())
    asyncio.run(r.run(settings=Settings(), spec=spec, profiles=[], ws=ws, env={}, emit=events.append))

    assert any(e["type"] == "assistant_text" for e in events)
    assert any(e["type"] == "result_meta" and e["completion"] == "DONE" for e in events)
    assert (ws / "output" / "article.md").read_text(encoding="utf-8").startswith("# 假成稿")
