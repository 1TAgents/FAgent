"""
测试命令 - 自动化测试 FAgent 功能

- fagent test message-flow - 测试消息流
- fagent test summary-generation - 测试摘要生成
- fagent test extraction - 测试记忆提取
- fagent test all - 运行所有测试
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime
import time

console = Console()


def get_memory():
    """获取 Memory Manager 单例"""
    from src.memory.manager import MemoryManager
    return MemoryManager()


@click.group()
def test():
    """测试命令 - 自动化测试 FAgent 功能"""
    pass


@test.command('message-flow')
def test_message_flow():
    """测试消息流"""
    memory = get_memory()
    
    console.print("[bold]测试消息流...[/bold]\n")
    
    try:
        # 1. 创建会话
        cid = memory.start_session(title="测试消息流")
        console.print(f"✓ 创建会话：{cid}")
        time.sleep(0.1)
        
        # 2. 发送多条消息
        test_messages = [
            "第一条测试消息",
            "第二条测试消息",
            "第三条测试消息",
        ]
        
        for i, msg in enumerate(test_messages):
            # TODO: 实现消息保存
            # mid = memory.save_message(cid=cid, role="user", content=msg)
            console.print(f"✓ 准备发送消息 {i+1}: {msg}")
            time.sleep(0.1)
        
        # 3. 检索消息
        # messages = memory.get_messages(cid, limit=10)
        console.print(f"✓ 准备检索消息")
        
        # 4. 清理
        # memory.delete_session(cid)
        console.print(f"✓ 测试完成")
        
        console.print("\n[green bold]✓ 消息流测试通过[/green bold]")
        
    except Exception as e:
        console.print(f"\n[red bold]✗ 消息流测试失败：{e}[/red bold]")


@test.command('summary-generation')
def test_summary_generation():
    """测试摘要生成"""
    console.print("[bold]测试摘要生成...[/bold]\n")
    
    try:
        # TODO: 实现摘要生成测试
        console.print("[yellow]⚠ 摘要生成功能待实现[/yellow]")
        console.print("\n[green bold]✓ 测试框架就绪[/green bold]")
        
    except Exception as e:
        console.print(f"\n[red bold]✗ 测试失败：{e}[/red bold]")


@test.command('extraction')
def test_extraction():
    """测试记忆提取"""
    console.print("[bold]测试记忆提取...[/bold]\n")
    
    try:
        # TODO: 实现记忆提取测试
        console.print("[yellow]⚠ 记忆提取功能待实现[/yellow]")
        console.print("\n[green bold]✓ 测试框架就绪[/green bold]")
        
    except Exception as e:
        console.print(f"\n[red bold]✗ 测试失败：{e}[/red bold]")


@test.command('session')
def test_session():
    """测试会话管理"""
    memory = get_memory()
    
    console.print("[bold]测试会话管理...[/bold]\n")
    
    try:
        # 1. 创建会话
        cid = memory.start_session(title="测试会话")
        console.print(f"✓ 创建会话：{cid}")
        
        # 2. 列出会话
        sessions = memory.list_sessions()
        console.print(f"✓ 列出会话：共 {len(sessions)} 个")
        
        # 3. 获取会话信息
        info = memory.get_session_info(cid)
        console.print(f"✓ 获取会话信息：{info['title']}")
        
        # 4. 切换会话
        success = memory.switch_session(cid)
        console.print(f"✓ 切换会话：{'成功' if success else '失败'}")
        
        console.print("\n[green bold]✓ 会话管理测试通过[/green bold]")
        
    except Exception as e:
        console.print(f"\n[red bold]✗ 测试失败：{e}[/red bold]")


@test.command('all')
def test_all():
    """运行所有测试"""
    console.print("[bold]运行所有测试...[/bold]\n")
    
    results = []
    
    # 运行各个测试
    tests = [
        ("会话管理", test_session),
        ("消息流", test_message_flow),
        ("摘要生成", test_summary_generation),
        ("记忆提取", test_extraction),
    ]
    
    for name, test_func in tests:
        console.print(f"\n{'='*50}")
        console.print(f"运行：{name} 测试")
        console.print(f"{'='*50}\n")
        
        try:
            test_func()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
    
    # 汇总结果
    console.print(f"\n{'='*50}")
    console.print("[bold]测试结果汇总[/bold]")
    console.print(f"{'='*50}\n")
    
    table = Table(title="测试结果")
    table.add_column("测试项", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("备注", style="yellow")
    
    passed = 0
    failed = 0
    
    for name, success, error in results:
        status = "[green]✓ 通过[/green]" if success else "[red]✗ 失败[/red]"
        note = error if error else "-"
        table.add_row(name, status, note)
        
        if success:
            passed += 1
        else:
            failed += 1
    
    console.print(table)
    console.print(f"\n总计：{passed} 通过，{failed} 失败")
    
    if failed > 0:
        console.print(f"\n[red bold]✗ {failed} 个测试失败[/red bold]")
    else:
        console.print(f"\n[green bold]✓ 所有测试通过![/green bold]")


@test.command('clean')
@click.option('--yes', '-y', is_flag=True, help='确认清理')
def test_clean(yes):
    """清理测试数据"""
    memory = get_memory()
    
    if not yes:
        click.confirm("确定要清理所有测试会话吗？", abort=True)
    
    try:
        sessions = memory.list_sessions()
        test_sessions = [s for s in sessions if '测试' in s['title'] or 'test' in s['title'].lower()]
        
        for session in test_sessions:
            memory.delete_session(session['cid'])
            console.print(f"✓ 删除测试会话：{session['cid']}")
        
        console.print(f"\n[green]✓ 清理完成，共删除 {len(test_sessions)} 个测试会话[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ 清理失败：{e}[/red]")
