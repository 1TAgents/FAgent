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
from datetime import datetime

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
    
    # 检查是否有当前会话
    if not memory.current_cid:
        # 自动创建新会话
        cid = memory.start_session()
        console.print(f"[dim]✓ 自动创建新会话：{cid}[/dim]\n")
    
    cid = memory.current_cid
    
    try:
        # TODO: 实现消息保存
        # mid = memory.save_message(cid=cid, role=role, content=content)
        
        console.print(Panel(
            f"[green]✓ 消息已发送[/green]\n\n"
            f"[bold]角色:[/bold] {role}\n"
            f"[bold]内容:[/bold] {content[:100]}{'...' if len(content) > 100 else ''}\n"
            f"[dim]会话：{cid}[/dim]\n\n"
            f"[yellow]⚠ 消息保存功能待实现[/yellow]",
            title="📤 FAgent 消息",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[red]✗ 发送失败：{e}[/red]")


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
        # TODO: 实现消息检索
        # messages = memory.get_messages(cid, limit=limit)
        
        console.print(Panel(
            f"[bold]会话:[/bold] {cid}\n"
            f"[bold]消息数:[/bold] 0 (待实现)\n\n"
            f"[yellow]⚠ 消息列表功能待实现[/yellow]",
            title="📋 FAgent 消息列表",
            border_style="blue"
        ))
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


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
        # TODO: 实现消息详情查询
        # detail = memory.get_message_detail(cid, mid)
        
        console.print(Panel(
            f"[bold]消息 ID:[/bold] {mid}\n"
            f"[bold]会话:[/bold] {cid}\n\n"
            f"[yellow]⚠ 消息详情功能待实现[/yellow]",
            title="📄 FAgent 消息详情",
            border_style="cyan"
        ))
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


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
        # TODO: 实现消息搜索
        # results = memory.search_messages(cid, query, limit=limit)
        
        console.print(Panel(
            f"[bold]搜索:[/bold] {query}\n"
            f"[bold]会话:[/bold] {cid}\n\n"
            f"[yellow]⚠ 消息搜索功能待实现[/yellow]",
            title="🔍 FAgent 消息搜索",
            border_style="yellow"
        ))
    except Exception as e:
        console.print(f"[red]✗ 搜索失败：{e}[/red]")
