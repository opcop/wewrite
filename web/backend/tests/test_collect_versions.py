from pathlib import Path
from app.platforms import PlatformProfile
from app.agent_runner import gate_passes, _extract_tags, _collect_platform_versions

def test_gate_passes():
    assert gate_passes(0.8, 0.3) is True
    assert gate_passes(0.5, 0.3) is False   # humanness 太低
    assert gate_passes(0.8, 0.7) is False   # 相似度太高
    assert gate_passes(None, None) is True   # 缺分不拦

def test_extract_tags():
    assert _extract_tags("正文\n\n#智能体 #AI落地 #2026") == ["智能体", "AI落地", "2026"]

def test_collect_reads_versions(tmp_path: Path):
    out = tmp_path / "output"
    out.mkdir()
    (out / "xiaohongshu.md").write_text(
        "# 我踩过的智能体坑\n\n说点真实的体验和细节。\n\n#智能体 #AI", encoding="utf-8")
    profiles = [PlatformProfile(id="xiaohongshu", label="小红书",
                output_kind="graphic_text", output_filename="xiaohongshu.md",
                needs_images=True)]

    class FakeJob:
        images = ["/artifacts/j/cover.png"]
        def emit(self, *a, **k): pass

    versions = _collect_platform_versions(
        FakeJob(), tmp_path, source_md="完全不同的源文章内容在这里随便写些字", profiles=profiles)
    assert len(versions) == 1
    v = versions[0]
    assert v["platform"] == "xiaohongshu"
    assert v["title"] == "我踩过的智能体坑"
    assert v["tags"] == ["智能体", "AI"]
    assert v["images"] == ["/artifacts/j/cover.png"]   # needs_images → 复用源图
    assert v["max_similarity"] < 0.5                    # 与源差异大
    assert v["status"] == "done"

def test_collect_marks_missing_failed(tmp_path: Path):
    (tmp_path / "output").mkdir()
    profiles = [PlatformProfile(id="douyin", label="抖音",
                output_kind="oral_script", output_filename="douyin.md")]
    class FakeJob:
        images = []
        def emit(self, *a, **k): pass
    versions = _collect_platform_versions(FakeJob(), tmp_path, "源", profiles)
    assert versions[0]["status"] == "failed"
