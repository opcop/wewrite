"""共享管道核心：构建 SDK options/prompt + 消费事件流。direct runner 与容器入口共用。
不得 import store / FastAPI —— 容器入口要能在最小依赖下导入本模块。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from .config import Settings
from .job_spec import JobSpec

# 与 SKILL.md frontmatter 的 allowed-tools 对齐
ALLOWED_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch", "TodoWrite"]

_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_COMPLETION_RE = re.compile(r"\b(DONE_WITH_CONCERNS|DONE|BLOCKED|NEEDS_CONTEXT)\b")

Emit = Callable[[dict], None]


def detect_completion(last_text: str | None, result_text: str | None) -> str:
    for blob in (result_text or "", last_text or ""):
        m = _COMPLETION_RE.search(blob)
        if m:
            return m.group(1)
    return "DONE"


def summarize_tool_input(name: str, tool_input: dict) -> str:
    if name == "Bash":
        return str(tool_input.get("command", ""))[:200]
    if name in ("Read", "Write", "Edit"):
        return str(tool_input.get("file_path", ""))
    if name in ("Glob", "Grep"):
        return str(tool_input.get("pattern", ""))
    if name in ("WebSearch", "WebFetch"):
        return str(tool_input.get("query") or tool_input.get("url", ""))
    return ""


async def consume_stream(message_iter, emit: Emit) -> str:
    """消费 Agent SDK 流，调 emit 发事件，返回最后一段 assistant 文本。"""
    last_text = ""
    async for message in message_iter:
        if isinstance(message, SystemMessage):
            continue
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text = block.text.strip()
                    if text:
                        last_text = text
                        emit({"type": "assistant_text", "text": text})
                elif isinstance(block, ToolUseBlock):
                    emit({"type": "tool_use", "name": block.name,
                          "detail": summarize_tool_input(block.name, block.input or {})})
                elif isinstance(block, ThinkingBlock):
                    continue
        elif isinstance(message, UserMessage):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    emit({"type": "tool_result", "is_error": bool(block.is_error)})
        elif isinstance(message, ResultMessage):
            completion = detect_completion(last_text, getattr(message, "result", None))
            emit({"type": "result_meta", "completion": completion,
                  "num_turns": getattr(message, "num_turns", None),
                  "total_cost_usd": getattr(message, "total_cost_usd", None),
                  "is_error": getattr(message, "is_error", False)})
    return last_text


def generate_system_prompt(settings: Settings) -> dict:
    body = (settings.skill_dir / "SKILL.md").read_text(encoding="utf-8")
    body = _FRONTMATTER.sub("", body, count=1).strip()
    note = (
        "\n\n---\n# 运行环境说明\n"
        "你正在云端为外部用户执行 WeWrite 公众号写作管道。\n"
        "- 本说明上方的内容来自 WeWrite 的 SKILL.md，是你要严格遵循的主管道。\n"
        "- `{skill_dir}` 指你当前的工作目录（cwd）。toolkit/scripts/references/personas 已就位。\n"
        "- 风格在 style.yaml；微信与图片密钥已通过环境变量注入（toolkit 会自动读取）。\n"
        "- 用户看不到你的中间思考，过程进度请用简短的一行行文本表达。\n"
    )
    return {"type": "preset", "preset": "claude_code", "append": body + note}


def generate_user_prompt(spec: JobSpec) -> str:
    mode = "交互模式（在选题/框架/配图处可暂停确认）" if spec.interactive else "全自动模式（一口气跑完 Step 1-8，不中途停）"
    if spec.publish:
        pub = "完成后把成稿推送到微信公众号草稿箱（appid/secret 已注入环境，可直接发布）。"
    else:
        pub = "只在本地生成并排版，不要推送草稿箱（视作 skip_publish 降级）。"
    return (
        f"{spec.prompt}\n\n"
        f"（{mode}。请按 SKILL.md 主管道 Step 1-8 完整执行；"
        f"每进入一步输出一行 `[N/8] 步骤名` 的文本进度。{pub} "
        f"最终把文章正文保存为 `output/article.md`（这是要交付给用户的正文）；"
        f"配图提示词、SEO 备注等辅助 Markdown 请另存到 `output/assets/` 子目录，"
        f"不要和正文一起堆在 output 顶层。）"
    )


def distribute_system_prompt(settings: Settings, profiles: list) -> dict:
    from .platforms import MAX_REWRITE_RETRIES
    guide = (settings.skill_dir / "references" / "multiplatform-rewrite.md").read_text(encoding="utf-8")
    briefs = "\n\n".join(
        f"### 平台：{p.label}（id={p.id}）\n"
        f"- 产出文件：output/{p.output_filename}\n"
        f"- 形态：{p.output_kind}；需配图：{p.needs_images}\n"
        f"- 规范：\n{p.rewrite_brief}"
        for p in profiles
    )
    body = (
        "你是 WeWrite 的多平台改写引擎。把 `output/source.md` 的源内容改写成下列各平台的适配版本。\n\n"
        f"{guide}\n\n## 本次目标平台\n{briefs}\n\n"
        "- 用户看不到你的中间思考，进度用简短一行行文本表达。\n"
        f"- 每个平台版本写完后跑质量门自查，不过则重写，最多重试 {MAX_REWRITE_RETRIES} 次。"
    )
    return {"type": "preset", "preset": "claude_code", "append": body}


def distribute_user_prompt(profiles: list) -> str:
    names = "、".join(p.label for p in profiles)
    files = "、".join(f"output/{p.output_filename}" for p in profiles)
    return (
        f"请把 output/source.md 改写为：{names}。\n"
        f"分别保存到：{files}。每进入一个平台输出一行 `[改写] 平台名` 的进度。\n"
        "严格遵守原创铁律（内容级真改、与源和彼此都拉开差异）与各平台规范，"
        "并对每个版本跑 humanness_score.py 与 similarity_check.py 自查。"
    )


def make_options_and_prompt(settings: Settings, spec: JobSpec, profiles: list,
                            env: dict, ws: Path) -> tuple[ClaudeAgentOptions, str]:
    if spec.kind == "distribute":
        system_prompt = distribute_system_prompt(settings, profiles)
        user_prompt = distribute_user_prompt(profiles)
    else:
        system_prompt = generate_system_prompt(settings)
        user_prompt = generate_user_prompt(spec)
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=ALLOWED_TOOLS,
        permission_mode="bypassPermissions",
        model=settings.model,
        cwd=str(ws),
        env=env,
        max_turns=settings.max_turns,
        setting_sources=None,
    )
    return options, user_prompt
