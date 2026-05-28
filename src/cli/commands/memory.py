"""
记忆查询命令 - 实现逐渐披露 API

- fagent memory overview - Level 1: 会话概览
- fagent memory messages - Level 2: 消息列表
- fagent memory detail <mid> - Level 3: 消息详情
- fagent memory tool <rid> - Level 4: 工具响应
- fagent memory expand <sid> - Level 5: 展开摘要
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()


def get_memory():
    """获取 Memory Manager 单例"""
    from src.memory.manager import MemoryManager
    return MemoryManager()


@click.group()
def memory():
    """记忆查询命令 - 逐渐披露 API"""
    pass


@memory.command('overview')
def memory_overview():
    """Level 1: 会话概览"""
    memory_mgr = get_memory()

    if not memory_mgr.current_cid:
        console.print("[yellow]暂无当前会话，请先创建或切换会话[/yellow]")
        console.print("\n使用 [cyan]fagent session new[/cyan] 创建会话")
        return

    cid = memory_mgr.current_cid

    try:
        info = memory_mgr.get_session_info(cid)
        if not info:
            console.print(f"[red]会话不存在：{cid}[/red]")
            return

        messages = memory_mgr.get_messages(cid, limit=100)
        summaries = memory_mgr.get_summaries(cid)

        # 统计各角色消息数
        role_counts = {}
        for msg in messages:
            role_counts[msg.role.value] = role_counts.get(msg.role.value, 0) + 1

        stats_lines = []
        for role, count in sorted(role_counts.items()):
            stats_lines.append(f"  {role}: {count}")

        # 最后一条消息时间
        last_msg_time = messages[-1].timestamp[:19] if messages else "-"

        console.print(Panel(
            f"[bold]会话 ID:[/bold] {cid}\n"
            f"[bold]标题:[/bold] {info['title'] or '-'}\n"
            f"[bold]状态:[/bold] {info['status']}\n"
            f"[bold]消息总数:[/bold] {len(messages)}\n"
            f"[bold]摘要数:[/bold] {len(summaries)}\n"
            f"[bold]最后活跃:[/bold] {last_msg_time}\n\n"
            f"[bold]消息分布:[/bold]\n"
            + "\n".join(stats_lines) if stats_lines else "  暂无消息",
            title="FAgent Memory - Level 1 概览",
            border_style="blue"
        ))
    except Exception as e:
        console.print(f"[red]查询失败：{e}[/red]")


@memory.command('messages')
@click.option('--limit', '-l', default=20, help='显示数量')
@click.option('--start', '-s', default=0, help='起始位置')
def memory_messages(limit, start):
    """Level 2: 消息列表（分页，带摘要标记）"""
    memory_mgr = get_memory()

    if not memory_mgr.current_cid:
        console.print("[yellow]暂无当前会话[/yellow]")
        return

    cid = memory_mgr.current_cid

    try:
        messages = memory_mgr.get_messages(cid, start=start, limit=limit)
        summaries = memory_mgr.get_summaries(cid)
        summary_mids = set()
        for s in summaries:
            for mid in s.covered_mids:
                summary_mids.add(mid)

        if not messages:
            console.print("[yellow]暂无消息[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("序号", style="dim", max_width=6)
        table.add_column("MID", style="cyan", max_width=20)
        table.add_column("角色", style="white")
        table.add_column("内容", style="yellow")
        table.add_column("摘要", style="green")

        for msg in messages:
            table.add_row(
                str(msg.sequence_num),
                msg.mid,
                msg.role.value,
                msg.content[:50],
                "已覆盖" if msg.mid in summary_mids else "-",
            )

        console.print(table)
        console.print(f"\n[dim]共 {len(messages)} 条消息 (offset={start})[/dim]")
    except Exception as e:
        console.print(f"[red]查询失败：{e}[/red]")


@memory.command('detail')
@click.argument('mid')
def memory_detail(mid):
    """Level 3: 单条消息详情（完整原始内容）"""
    memory_mgr = get_memory()

    if not memory_mgr.current_cid:
        console.print("[yellow]暂无当前会话[/yellow]")
        return

    cid = memory_mgr.current_cid

    try:
        msg = memory_mgr.get_message(cid, mid)
        if not msg:
            console.print(f"[red]消息不存在：{mid}[/red]")
            return

        summaries = memory_mgr.get_summaries(cid)
        covered_by = [s for s in summaries if mid in s.covered_mids]

        lines = [
            f"[bold]消息 ID:[/bold] {msg.mid}",
            f"[bold]会话:[/bold] {msg.cid}",
            f"[bold]角色:[/bold] {msg.role.value}",
            f"[bold]时间:[/bold] {msg.timestamp[:19] if msg.timestamp else '-'}",
            f"[bold]序号:[/bold] {msg.sequence_num}",
            f"[bold]状态:[/bold] {msg.status.value}",
            "",
            f"[bold]内容:[/bold]",
            msg.content,
        ]

        if covered_by:
            lines.append("")
            lines.append(f"[bold]被 {len(covered_by)} 个摘要覆盖:[/bold]")
            for s in covered_by:
                lines.append(f"  - {s.sid}: {s.summary[:60]}...")

        console.print(Panel("\n".join(lines), title="FAgent Memory - Level 3 消息详情", border_style="green"))
    except Exception as e:
        console.print(f"[red]查询失败：{e}[/red]")


@memory.command('tool')
@click.argument('rid')
@click.option('--full', '-f', is_flag=True, help='加载完整内容（懒加载）')
def memory_tool(rid, full):
    """Level 4: 工具响应详情（摘要 + 懒加载完整内容）"""
    memory_mgr = get_memory()

    try:
        response = memory_mgr.get_tool_response(rid)
        if not response:
            console.print(f"[red]工具响应不存在：{rid}[/red]")
            return

        lines = [
            f"[bold]响应 ID:[/bold] {response.rid}",
            f"[bold]会话:[/bold] {response.cid}",
            f"[bold]消息:[/bold] {response.mid}",
            f"[bold]工具:[/bold] {response.tool_name}",
            f"[bold]存储类型:[/bold] {response.storage_type.value}",
            f"[bold]响应大小:[/bold] {response.response_size} bytes",
            f"[bold]创建时间:[/bold] {response.created_at[:19]}",
            "",
            f"[bold]摘要:[/bold] {response.summary}",
        ]

        if response.key_data:
            lines.append("")
            lines.append("[bold]关键数据:[/bold]")
            for k, v in response.key_data.items():
                lines.append(f"  {k}: {v}")

        if full and response.inline_content:
            lines.append("")
            lines.append("[bold]完整内容:[/bold]")
            lines.append(response.inline_content)
        elif response.can_load_full and not full:
            lines.append("")
            lines.append(f"[dim]使用 --full 加载完整内容（{response.response_size} bytes）[/dim]")

        console.print(Panel("\n".join(lines), title="FAgent Memory - Level 4 工具响应", border_style="yellow"))
    except Exception as e:
        console.print(f"[red]查询失败：{e}[/red]")


@memory.command('expand')
@click.argument('sid')
@click.option('--limit', '-l', default=10, help='显示消息数量')
def memory_expand(sid, limit):
    """Level 5: 展开摘要（查看覆盖的原始消息）"""
    memory_mgr = get_memory()

    try:
        summary = memory_mgr.get_summary(sid)
        if not summary:
            console.print(f"[red]摘要不存在：{sid}[/red]")
            return

        covered_messages = []
        for mid in summary.covered_mids:
            msg = memory_mgr.get_message(summary.cid, mid)
            if msg:
                covered_messages.append(msg)

        lines = [
            f"[bold]摘要 ID:[/bold] {summary.sid}",
            f"[bold]会话:[/bold] {summary.cid}",
            f"[bold]类型:[/bold] {summary.summary_type}",
            f"[bold]覆盖消息数:[/bold] {summary.message_count}",
            "",
            f"[bold]摘要内容:[/bold]",
            summary.summary,
        ]

        if summary.key_points:
            lines.append("")
            lines.append("[bold]要点:[/bold]")
            for kp in summary.key_points:
                lines.append(f"  - {kp}")

        if covered_messages:
            lines.append("")
            lines.append(f"[bold]覆盖的消息 (前 {min(limit, len(covered_messages))} 条):[/bold]")
            for msg in covered_messages[:limit]:
                lines.append(f"  {msg.mid} ({msg.role.value}): {msg.content[:60]}...")

        console.print(Panel("\n".join(lines), title="FAgent Memory - Level 5 摘要展开", border_style="magenta"))
    except Exception as e:
        console.print(f"[red]查询失败：{e}[/red]")


@memory.command('search')
@click.argument('query')
@click.option('--limit', '-l', default=10, help='显示数量')
def memory_search(query, limit):
    """搜索消息（在完整内容中搜索）"""
    memory_mgr = get_memory()

    if not memory_mgr.current_cid:
        console.print("[yellow]暂无当前会话[/yellow]")
        return

    cid = memory_mgr.current_cid

    try:
        messages = memory_mgr.get_messages(cid, limit=200)
        results = [m for m in messages if query.lower() in m.content.lower()]
        results = results[:limit]

        if not results:
            console.print(f"[yellow]搜索未找到匹配 '{query}' 的消息[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("MID", style="cyan", max_width=20)
        table.add_column("角色", style="white")
        table.add_column("内容", style="yellow")

        for msg in results:
            idx = msg.content.lower().index(query.lower())
            start = max(0, idx - 20)
            end = min(len(msg.content), idx + len(query) + 40)
            snippet = msg.content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(msg.content):
                snippet = snippet + "..."

            table.add_row(msg.mid, msg.role.value, snippet)

        console.print(table)
        console.print(f"\n[dim]找到 {len(results)} 条匹配消息[/dim]")
    except Exception as e:
        console.print(f"[red]搜索失败：{e}[/red]")
