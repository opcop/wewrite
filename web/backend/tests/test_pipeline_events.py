import asyncio
from dataclasses import dataclass
from app import pipeline

@dataclass
class _Text: text: str
@dataclass
class _ToolUse: name: str; input: dict; id: str = "t1"
@dataclass
class _ToolResult: tool_use_id: str = "t1"; is_error: bool = False; content=None
@dataclass
class _Assistant: content: list
@dataclass
class _User: content: list
@dataclass
class _Result: result: str = "DONE"; num_turns: int = 7; total_cost_usd: float = 0.1; is_error: bool = False

def test_consume_stream_maps_events(monkeypatch):
    monkeypatch.setattr(pipeline, "TextBlock", _Text)
    monkeypatch.setattr(pipeline, "ToolUseBlock", _ToolUse)
    monkeypatch.setattr(pipeline, "ToolResultBlock", _ToolResult)
    monkeypatch.setattr(pipeline, "ThinkingBlock", type("T", (), {}))
    monkeypatch.setattr(pipeline, "AssistantMessage", _Assistant)
    monkeypatch.setattr(pipeline, "UserMessage", _User)
    monkeypatch.setattr(pipeline, "SystemMessage", type("S", (), {}))
    monkeypatch.setattr(pipeline, "ResultMessage", _Result)

    async def gen():
        yield _Assistant(content=[_Text("[1/8] 环境")])
        yield _Assistant(content=[_ToolUse(name="Bash", input={"command": "ls -la /tmp"})])
        yield _User(content=[_ToolResult(is_error=False)])
        yield _Result()

    events = []
    last = asyncio.run(pipeline.consume_stream(gen(), events.append))
    types = [e["type"] for e in events]
    assert types == ["assistant_text", "tool_use", "tool_result", "result_meta"]
    assert events[1]["name"] == "Bash" and "ls -la" in events[1]["detail"]
    assert events[-1]["completion"] == "DONE" and events[-1]["num_turns"] == 7
    assert last == "[1/8] 环境"
