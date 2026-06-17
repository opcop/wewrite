"""容器模式下，工作区里没有 toolkit/ 软链；预览/评分必须从 skill_dir 跑通。"""
from pathlib import Path

from app.agent_runner import _generate_preview, _humanness_best_effort


def _bare_container_ws(tmp_path: Path) -> Path:
    # 模拟 container 模式工作区：只有可写的 output/，没有任何 skill 软链
    ws = tmp_path / "ws"
    (ws / "output").mkdir(parents=True)
    (ws / "output" / "article.md").write_text(
        "# 测试标题\n\n这是一段用于渲染预览的正文内容，足够长以便转换。\n", encoding="utf-8")
    assert not (ws / "toolkit").exists()  # 关键：工作区没有 toolkit 软链
    return ws


def test_preview_generates_without_workspace_toolkit(tmp_path: Path):
    ws = _bare_container_ws(tmp_path)
    html = _generate_preview(ws, ws / "output" / "article.md", theme="professional-clean")
    assert html is not None and "<" in html  # 产出了 HTML，没有因缺 toolkit 软链而失败


def test_humanness_runs_without_workspace_scripts(tmp_path: Path):
    ws = _bare_container_ws(tmp_path)
    # 评分脚本从 skill_dir 跑；这里只断言不抛、返回 float 或 None（降级），不依赖 ws/scripts
    score = _humanness_best_effort(ws, "article.md")
    assert score is None or isinstance(score, float)
