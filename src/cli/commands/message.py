"""
消息操作命令

- fagent message send "内容" - 发送消息
- fagent message list - 列出消息
- fagent message show <mid> - 显示详情
- fagent message search "关键词" - 搜索消息
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
def message():
    """消息操作命令"""
    pass


@message.command('send')
@click.argument('content')
@click.option('--role', '-r', default='user',
              type=click.Choice(['user', 'assistant', 'system']),
              help='消息角色')
def message_send(content, role):
    """发送消息"""
    memory = get_memory()

    if not memory.current_cid:
        cid = memory.start_session()
        console.print(f"[dim]自动创建新会话：{cid}[/dim]\n")

    cid = memory.current_cid

    try:
        mid = memory.save_message(cid=cid, role=role, content=content)

        console.print(Panel(
            f"[green]消息已发送[/green]\n\n"
            f"[bold]角色:[/bold] {role}\n"
            f"[bold]内容:[/bold] {content[:100]}{'...' if len(content) > 100 else ''}\n"
            f"[bold]会话:[/bold] {cid}\n"
            f"[bold]消息 ID:[/bold] {mid}",
            title="FAgent 消息",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[red]发送失败：{e}[/red]")


@message.command('list')
@click.option('--limit', '-l', default=20, help='显示数量')
@click.option('--role', '-r', default=None,
              type=click.Choice(['user', 'assistant', 'system']),
              help='按角色过滤')
def message_list(limit, role):
    """列出消息"""
    memory = get_memory()

    if not memory.current_cid:
        console.print("[yellow]暂无当前会话，请先创建或切换会话[/yellow]")
        console.print("\n使用 [cyan]fagent session new[/cyan] 创建会话")
        return

    cid = memory.current_cid

    try:
        messages = memory.get_messages(cid, limit=limit)

        if role:
            messages = [m for m in messages if m.role.value == role]

        if not messages:
            console.print("[yellow]暂无消息[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("MID", style="cyan", max_width=20)
        table.add_column("角色", style="white")
        table.add_column("内容", style="yellow")
        table.add_column("时间", style="dim", max_width=20)

        for msg in messages:
            table.add_row(
                msg.mid,
                msg.role.value,
                msg.content[:60],
                msg.timestamp[:19] if msg.timestamp else "-",
            )

        console.print(table)
        console.print(f"\n[dim]共 {len(messages)} 条消息[/dim]")
    except Exception as e:
        console.print(f"[red]查询失败：{e}[/red]")


@message.command('show')
@click.argument('mid')
def message_show(mid):
    """显示消息详情"""
    memory = get_memory()

    if not memory.current_cid:
        console.print("[yellow]暂无当前会话[/yellow]")
        return

    cid = memory.current_cid

    try:
        msg = memory.get_message(cid, mid)
        if not msg:
            console.print(f"[red]消息不存在：{mid}[/red]")
            return

        console.print(Panel(
            f"[bold]消息 ID:[/bold] {msg.mid}\n"
            f"[bold]会话:[/bold] {msg.cid}\n"
            f"[bold]角色:[/bold] {msg.role.value}\n"
            f"[bold]时间:[/bold] {msg.timestamp[:19] if msg.timestamp else '-'}\n"
            f"[bold]序号:[/bold] {msg.sequence_num}\n\n"
            f"{msg.content}",
            title="FAgent 消息详情",
            border_style="cyan"
        ))
    except Exception as e:
        console.print(f"[red]查询失败：{e}[/red]")


@message.command('search')
@click.argument('query')
@click.option('--limit', '-l', default=10, help='显示数量')
def message_search(query, limit):
    """搜索消息"""
    memory = get_memory()

    if not memory.current_cid:
        console.print("[yellow]暂无当前会话[/yellow]")
        return

    cid = memory.current_cid

    try:
        messages = memory.get_messages(cid, limit=200)
        results = [m for m in messages if query.lower() in m.content.lower()]
        results = results[:limit]

        if not results:
            console.print(f"[yellow]未找到匹配 '{query}' 的消息[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("MID", style="cyan", max_width=20)
        table.add_column("角色", style="white")
        table.add_column("内容", style="yellow")

        for msg in results:
            # 高亮匹配片段
            idx = msg.content.lower().index(query.lower())
            start = max(0, idx - 20)
            end = min(len(msg.content), idx + len(query) + 40)
            snippet = msg.content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(msg.content):
                snippet = snippet + "..."

            table.add_row(
                msg.mid,
                msg.role.value,
                snippet,
            )

        console.print(table)
        console.print(f"\n[dim]找到 {len(results)} 条匹配消息[/dim]")
    except Exception as e:
        console.print(f"[red]搜索失败：{e}[/red]")
