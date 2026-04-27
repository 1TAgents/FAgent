"""
MCP Chain Trace

为 MCP 和 datasource 层补充结构化 JSONL 日志，便于按 rid/cid/mid 回放工具调用链。
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.core.context import get_context


LOG_DIR = Path(__file__).resolve().parents[2] / "logs" / "mcp"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_chain_event(
    layer: str,
    event: str,
    **payload: Any,
) -> None:
    """追加一条 MCP 结构化 chain 事件"""
    ctx = get_context()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "service": "mcp",
        "layer": layer,
        "event": event,
        "rid": ctx.get("rid"),
        "cid": ctx.get("cid"),
        "mid": ctx.get("mid"),
    }

    for key, value in payload.items():
        if value is not None:
            entry[key] = value

    logfile = LOG_DIR / f"chain_{datetime.now():%Y-%m-%d}.jsonl"
    with logfile.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
