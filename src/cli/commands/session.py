"""
会话管理命令

- fagent session new - 创建会话
- fagent session list - 列出会话
- fagent session switch <cid> - 切换会话
- fagent session info - 会话信息
- fagent session delete <cid> - 删除会话
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime

console = Console()


def get_memory():
    """获取 Memory Manager 单例"""
    from src.memory.manager import MemoryManager
    return MemoryManager()


@click.group()
def session():
    """会话管理命令"""
    pass


@session.command('new')
@click.option('--title', '-t', default=None, help='会话标题')
def session_new(title):
    """创建新会话"""
    memory = get_memory()
    try:
        cid = memory.start_session(title)
        console.print(Panel(
            f"[green]✓ 创建新会话成功[/green]\n\n"
            f"[bold cyan]CID:[/bold cyan] {cid}\n"
            f"[dim]创建时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
            title="📊 FAgent 会话",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[red]✗ 创建失败：{e}[/red]")


@session.command('list')
@click.option('--status', '-s', default='active', 
              type=click.Choice(['active', 'deleted', 'all']),
              help='会话状态')
@click.option('--limit', '-l', default=20, help='显示数量')
def session_list(status, limit):
    """列出所有会话"""
    memory = get_memory()
    try:
        if status == 'all':
            sessions = memory.list_sessions()
        else:
            sessions = memory.list_sessions(status=status)
        
        if not sessions:
            console.print("[yellow]暂无会话[/yellow]")
            return
        
        table = Table(title="📊 FAgent 会话列表", show_header=True, header_style="bold magenta")
        table.add_column("CID", style="cyan", max_width=40)
        table.add_column("标题", style="white")
        table.add_column("创建时间", style="green")
        table.add_column("消息数", justify="right", style="yellow")
        table.add_column("状态", style="blue")
        
        for s in sessions[:limit]:
            # 标记当前会话
            cid_display = s['cid']
            if s['cid'] == memory.current_cid:
                cid_display = f"[bold green]→ {cid_display}[/bold green]"
            
            table.add_row(
                cid_display,
                s['title'] or "-",
                s['created_at'][:16],
                str(s['message_count']),
                s['status']
            )
        
        console.print(table)
        console.print(f"\n[dim]共 {len(sessions)} 个会话，显示前 {min(limit, len(sessions))} 个[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


@session.command('switch')
@click.argument('cid')
def session_switch(cid):
    """切换会话"""
    memory = get_memory()
    try:
        success = memory.switch_session(cid)
        if success:
            info = memory.get_session_info(cid)
            console.print(Panel(
                f"[green]✓ 已切换到会话[/green]\n\n"
                f"[bold cyan]CID:[/bold cyan] {cid}\n"
                f"[bold]标题:[/bold] {info['title'] or '-'}\n"
                f"[dim]消息数：{info['message_count']}[/dim]",
                title="📊 FAgent 会话",
                border_style="green"
            ))
        else:
            console.print(f"[red]✗ 会话不存在：{cid}[/red]")
    except Exception as e:
        console.print(f"[red]✗ 切换失败：{e}[/red]")


@session.command('info')
@click.argument('cid', required=False)
def session_info(cid):
    """显示会话信息"""
    memory = get_memory()
    try:
        info = memory.get_session_info(cid)
        if not info:
            console.print("[yellow]未找到会话[/yellow]")
            return
        
        current_marker = " [green](当前)[/green]" if info['cid'] == memory.current_cid else ""
        
        console.print(Panel(
            f"[bold cyan]CID:[/bold cyan] {info['cid']}{current_marker}\n"
            f"[bold]标题:[/bold] {info['title'] or '-'}\n"
            f"[bold]状态:[/bold] {info['status']}\n"
            f"[bold]消息数:[/bold] {info['message_count']}\n"
            f"[bold]创建时间:[/bold] {info['created_at'][:19]}\n"
            f"[bold]更新时间:[/bold] {info['updated_at'][:19]}",
            title="📊 FAgent 会话详情",
            border_style="blue"
        ))
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


@session.command('delete')
@click.argument('cid')
@click.option('--yes', '-y', is_flag=True, help='确认删除')
def session_delete(cid, yes):
    """删除会话（软删除）"""
    memory = get_memory()
    try:
        # 检查是否是当前会话
        if cid == memory.current_cid:
            console.print("[yellow]⚠ 不能删除当前会话，请先切换到其他会话[/yellow]")
            return
        
        # 获取会话信息
        info = memory.get_session_info(cid)
        if not info:
            console.print(f"[red]✗ 会话不存在：{cid}[/red]")
            return
        
        # 确认删除
        if not yes:
            click.confirm(
                f"确定要删除会话 {cid} 吗？\n"
                f"标题：{info['title'] or '-'}\n"
                f"消息数：{info['message_count']}",
                abort=True
            )
        
        # 执行删除
        success = memory.delete_session(cid)
        if success:
            console.print(Panel(
                f"[green]✓ 会话已删除[/green]\n\n"
                f"[dim]会话 {cid} 已标记为 deleted 状态[/dim]",
                title="📊 FAgent 会话",
                border_style="green"
            ))
        else:
            console.print(f"[red]✗ 删除失败[/red]")
    except Exception as e:
        console.print(f"[red]✗ 删除失败：{e}[/red]")
