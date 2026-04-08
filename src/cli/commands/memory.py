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
        # TODO: 实现会话概览 API
        # overview = memory_mgr.api.get_conversation_overview(cid)
        
        console.print(Panel(
            f"[bold]会话 ID:[/bold] {cid}\n\n"
            f"[yellow]⚠ 会话概览功能待实现[/yellow]\n\n"
            f"[dim]该功能将显示:[/dim]\n"
            f"- 摘要列表\n"
            f"- 每个摘要的覆盖消息数\n"
            f"- 快速导航提示",
            title="📊 FAgent Memory - Level 1 概览",
            border_style="blue"
        ))
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


@memory.command('messages')
@click.option('--limit', '-l', default=20, help='显示数量')
@click.option('--start', '-s', default=0, help='起始位置')
def memory_messages(limit, start):
    """Level 2: 消息列表（分页，带摘要标记）"""
    api = get_api()
    memory_mgr = get_memory()
    
    if not memory_mgr.current_cid:
        console.print("[yellow]暂无当前会话[/yellow]")
        return
    
    cid = memory_mgr.current_cid
    
    try:
        result = api.get_conversation_messages(cid, start=start, limit=limit)
        
        console.print(Panel(
            f"[bold]会话 ID:[/bold] {result['cid']}\n"
            f"[bold]消息数:[/bold] {len(result['messages'])}\n"
            f"[green]✓ 消息列表[/green]",
            title="📋 FAgent Memory - Level 2 消息列表",
            border_style="cyan"
        ))
        
        if result['messages']:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("MID", style="cyan", max_width=20)
            table.add_column("角色", style="white")
            table.add_column("内容", style="yellow")
            table.add_column("摘要", style="green")
            
            for msg in result['messages']:
                table.add_row(
                    msg['mid'],
                    msg['role'],
                    msg['content_preview'][:50],
                    "✓" if msg['has_summary'] else "-"
                )
            
            console.print(table)
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


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
        # TODO: 实现消息详情 API
        # detail = memory_mgr.api.get_message_detail(cid, mid)
        
        console.print(Panel(
            f"[bold]消息 ID:[/bold] {mid}\n"
            f"[bold]会话 ID:[/bold] {cid}\n\n"
            f"[yellow]⚠ 消息详情功能待实现[/yellow]\n\n"
            f"[dim]该功能将显示:[/dim]\n"
            f"- 完整原始内容（不截断）\n"
            f"- 消息元数据（时间戳、角色、序号）\n"
            f"- 关联的摘要\n"
            f"- 导航提示",
            title="📄 FAgent Memory - Level 3 消息详情",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


@memory.command('tool')
@click.argument('rid')
@click.option('--full', '-f', is_flag=True, help='加载完整内容（懒加载）')
def memory_tool(rid, full):
    """Level 4: 工具响应详情（摘要 + 懒加载完整内容）"""
    memory_mgr = get_memory()
    
    if not memory_mgr.current_cid:
        console.print("[yellow]暂无当前会话[/yellow]")
        return
    
    cid = memory_mgr.current_cid
    
    try:
        # TODO: 实现工具响应 API
        # tool_detail = memory_mgr.api.get_tool_response_detail(rid)
        
        console.print(Panel(
            f"[bold]响应 ID:[/bold] {rid}\n"
            f"[bold]会话 ID:[/bold] {cid}\n"
            f"[bold]完整内容:[/bold] {'是' if full else '否'}\n\n"
            f"[yellow]⚠ 工具响应功能待实现[/yellow]\n\n"
            f"[dim]该功能将显示:[/dim]\n"
            f"- 工具名称和输入\n"
            f"- 响应摘要\n"
            f"- 关键数据（结构化）\n"
            f"- 完整内容（懒加载，--full 选项）",
            title="🔧 FAgent Memory - Level 4 工具响应",
            border_style="yellow"
        ))
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


@memory.command('expand')
@click.argument('sid')
@click.option('--limit', '-l', default=10, help='显示消息数量')
def memory_expand(sid, limit):
    """Level 5: 展开摘要（查看覆盖的原始消息）"""
    api = get_api()
    
    try:
        result = api.expand_summary(sid)
        
        if "error" in result:
            console.print(f"[red]✗ {result['error']}[/red]")
            return
        
        console.print(Panel(
            f"[bold]摘要 ID:[/bold] {result['sid']}\n"
            f"[bold]覆盖消息数:[/bold] {result['message_count']}\n"
            f"[green]✓ 摘要展开[/green]",
            title="🔍 FAgent Memory - Level 5 摘要展开",
            border_style="magenta"
        ))
        
        console.print(f"\n[bold]摘要内容:[/bold]\n{result['summary']['summary']}")
        
        if result['covered_messages']:
            console.print(f"\n[bold]覆盖的消息:[/bold]")
            for msg in result['covered_messages'][:limit]:
                console.print(f"  • {msg['mid']} ({msg['role']}): {msg['content'][:50]}...")
    except Exception as e:
        console.print(f"[red]✗ 查询失败：{e}[/red]")


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
        # TODO: 实现搜索 API
        # results = memory_mgr.api.search_messages(cid, query, limit=limit)
        
        console.print(Panel(
            f"[bold]搜索词:[/bold] {query}\n"
            f"[bold]会话 ID:[/bold] {cid}\n"
            f"[bold]限制:[/bold] {limit}\n\n"
            f"[yellow]⚠ 搜索功能待实现[/yellow]\n\n"
            f"[dim]该功能将显示:[/dim]\n"
            f"- 匹配的消息列表\n"
            f"- 高亮显示匹配内容\n"
            f"- 消息元数据",
            title="🔎 FAgent Memory - 搜索",
            border_style="white"
        ))
    except Exception as e:
        console.print(f"[red]✗ 搜索失败：{e}[/red]")
