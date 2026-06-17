import importlib

_P1_ENV_KEYS = (
    "WEWRITE_RUNNER", "WEWRITE_MAX_CONCURRENT_JOBS", "WEWRITE_MAX_PER_USER_JOBS",
    "WEWRITE_JOB_IMAGE", "WEWRITE_JOB_CPUS", "WEWRITE_JOB_MEMORY",
    "WEWRITE_JOB_PIDS", "WEWRITE_JOB_TIMEOUT", "WEWRITE_JOB_NETWORK",
)

def _fresh_settings(monkeypatch, **env):
    # 先清掉所有 P1 键，保证未显式设置的项落到代码默认值（不受脏环境影响）
    for k in _P1_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import app.config as cfg
    importlib.reload(cfg)
    return cfg.Settings()

def test_p1_defaults(monkeypatch):
    s = _fresh_settings(monkeypatch)
    assert s.runner == "direct"
    assert s.max_concurrent_jobs == 3
    assert s.max_per_user_jobs == 1
    assert s.job_image == "wewrite-job:latest"
    assert s.job_cpus == "2"
    assert s.job_memory == "2g"
    assert s.job_pids == 512
    assert s.job_timeout == 1200.0
    assert s.job_network == "wewrite-jobs"

def test_p1_overrides(monkeypatch):
    s = _fresh_settings(monkeypatch, WEWRITE_RUNNER="container",
                        WEWRITE_MAX_CONCURRENT_JOBS="5", WEWRITE_MAX_PER_USER_JOBS="2")
    assert s.runner == "container"
    assert s.max_concurrent_jobs == 5
    assert s.max_per_user_jobs == 2
