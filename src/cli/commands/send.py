"""
Send 命令 — 通过 Agent 全链路发送消息

用法:
    fagent send "你好"                      # 流式发送
    fagent send "贵州茅台现在多少钱" --no-stream  # 非流式
    fagent send "测试" -m mimo-v2-flash      # 指定模型
    fagent send "分析" -n 5                  # 历史条数限制
"""

import asyncio
import sys
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


def get_memory():
    from src.memory.manager import MemoryManager
    return MemoryManager()


def get_backend_client():
    from src.cli.api_client import BackendClient
    return BackendClient()


def _is_valid_backend_cid(cid: Optional[str]) -> bool:
    """判断 cid 是否为后端可用的整数 cid。"""
    if not cid:
        return False
    try:
        int(cid)
        return True
    except ValueError:
        return False


def _run(coro):
    """Run an async backend call from the synchronous Click command."""
    return asyncio.run(coro)


async def _send_stream(backend, memory, cid: int, message: str,
                       model: Optional[str], history_limit: Optional[int]):
    """流式发送：逐块显示 SSE 响应。"""
    # 保存用户消息到本地 Memory
    try:
        memory.save_message(cid=str(cid), role="user", content=message)
    except Exception:
        pass  # 本地存储失败不阻断流程

    console.print()
    console.print("[dim] 正在思考...\n[/dim]")

    full_content = ""
    try:
        async for chunk in backend.send_stream(
            cid=cid,
            message=message,
            model=model,
            history_limit=history_limit,
        ):
            if not full_content:
                # 首次输出，清除 "正在思考..."
                console.rule("[dim]Agent 回复[/dim]", style="dim")
                console.print()
            console.print(chunk, end="")
            full_content += chunk
    except Exception as e:
        if full_content:
            console.print()
        console.print(f"\n[red]流式传输中断：{e}[/red]")
        if full_content:
            console.print("[dim]已接收部分内容，仍会保存到本地[/dim]")

    # 保存助手回复到本地 Memory
    if full_content:
        try:
            memory.save_message(cid=str(cid), role="assistant", content=full_content)
        except Exception:
            pass

    console.print()
    return full_content


async def _send_non_stream(backend, memory, cid: int, message: str,
                           model: Optional[str], history_limit: Optional[int]):
    """非流式发送：等待完整回复后 Markdown 渲染。"""
    # 保存用户消息
    try:
        memory.save_message(cid=str(cid), role="user", content=message)
    except Exception:
        pass

    console.print()
    console.print("[dim]正在等待 Agent 回复...[/dim]")

    try:
        content = await backend.send_non_stream(
            cid=cid,
            message=message,
            model=model,
            history_limit=history_limit,
        )
    except Exception as e:
        console.print(f"[red]请求失败：{e}[/red]")
        return ""

    # 保存助手回复
    if content:
        try:
            memory.save_message(cid=str(cid), role="assistant", content=content)
        except Exception:
            pass

    console.print()
    console.rule("[dim]Agent 回复[/dim]", style="dim")
    console.print()
    console.print(Markdown(content))
    console.print()

    return content


@click.command()
@click.argument("message", required=True)
@click.option("--model", "-m", default=None, help="指定模型")
@click.option("--no-stream", is_flag=True, help="非流式模式（等待完整回复）")
@click.option("--history-limit", "-n", type=int, default=None, help="历史消息条数限制")
def send(message: str, model: Optional[str], no_stream: bool,
         history_limit: Optional[int]):
    """发送消息给 Agent 并流式显示回复

    通过后端 API 调用完整的 Agent 链路
    （Router → ReAct → LLM → Tools）。

    示例:

        fagent send "你好"

        fagent send "贵州茅台现在多少钱" --no-stream

        fagent send "分析下科技股" -m mimo-v2-flash -n 5
    """
    backend = get_backend_client()
    memory = get_memory()

    # 1. 检查后端可用性
    try:
        healthy = _run(backend.health_check())
    except Exception:
        healthy = False

    if not healthy:
        console.print(Panel(
            "[red]后端服务不可达[/red]\n\n"
            "请先启动后端服务：\n"
            "  [cyan].venv/bin/python -m uvicorn backend.api.main:app --port 8000[/cyan]\n\n"
            f"当前后端地址：[cyan]{backend.base_url}[/cyan]\n"
            "如需修改，请设置 [cyan]FAGENT_BACKEND_URL[/cyan]。",
            title="连接错误",
            border_style="red",
        ))
        sys.exit(1)

    # 2. 确定 cid：如果是后端整数 cid 直接复用，否则创建新 session
    raw_cid = memory.current_cid
    if _is_valid_backend_cid(raw_cid):
        cid = int(raw_cid)
    else:
        # 当前 cid 是字符串（MemoryManager 格式）或不存在，创建后端 session
        try:
            cid = _run(backend.create_session(title="CLI Session"))
            # 将后端整数 cid 保存为当前 cid
            memory.current_cid = str(cid)
            console.print(f"[dim]已创建后端会话：cid={cid}[/dim]\n")
        except Exception as e:
            console.print(f"[red]创建会话失败：{e}[/red]")
            sys.exit(1)

    # 3. 发送消息
    if no_stream:
        content = _run(_send_non_stream(backend, memory, cid, message, model, history_limit))
    else:
        content = _run(_send_stream(backend, memory, cid, message, model, history_limit))

    if not content:
        sys.exit(1)
