"""
测试命令 - 自动化测试 FAgent 功能

- fagent test message-flow - 测试消息流
- fagent test summary-generation - 测试摘要生成
- fagent test extraction - 测试记忆提取
- fagent test session - 测试会话管理
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


# ==================== 核心测试逻辑（无 Click 装饰器） ====================


def run_test_session():
    """测试会话管理（核心逻辑）"""
    memory = get_memory()

    # 1. 创建会话
    cid = memory.start_session(title="测试会话")
    console.print(f"  创建会话：{cid}")

    # 2. 列出会话
    sessions = memory.list_sessions()
    assert len(sessions) >= 1, "会话列表为空"
    console.print(f"  列出会话：共 {len(sessions)} 个")

    # 3. 获取会话信息
    info = memory.get_session_info(cid)
    assert info is not None, "会话信息为 None"
    assert info['title'] == "测试会话", f"标题不匹配: {info['title']}"
    console.print(f"  获取会话信息：{info['title']}")

    # 4. 切换会话
    success = memory.switch_session(cid)
    assert success, "切换会话失败"
    console.print("  切换会话：成功")

    # 5. 清理
    other_cid = memory.start_session(title="临时会话")
    deleted = memory.delete_session(cid)
    assert deleted, "删除会话失败"
    console.print(f"  删除会话：{cid}")

    memory._current_cid = None
    memory.delete_session(other_cid)


def run_test_message_flow():
    """测试消息流（核心逻辑）"""
    memory = get_memory()

    # 1. 创建会话
    cid = memory.start_session(title="测试消息流")
    console.print(f"  创建会话：{cid}")

    # 2. 发送多条消息
    test_messages = [
        "第一条测试消息",
        "第二条测试消息",
        "第三条测试消息",
    ]

    for i, msg in enumerate(test_messages):
        mid = memory.save_message(cid=cid, role="user", content=msg)
        console.print(f"  发送消息 {i+1}: {msg} -> {mid}")

    # 3. 检索消息
    messages = memory.get_messages(cid, limit=10)
    console.print(f"  检索到 {len(messages)} 条消息")

    assert len(messages) == len(test_messages), \
        f"期望 {len(test_messages)} 条，实际 {len(messages)} 条"

    # 4. 验证消息内容
    for i, msg in enumerate(messages):
        assert msg.content == test_messages[i], \
            f"消息 {i} 内容不匹配: {msg.content} != {test_messages[i]}"
    console.print("  消息内容验证通过")

    # 5. 清理
    memory._current_cid = None
    memory.delete_session(cid)


def run_test_summary_generation():
    """测试摘要生成（核心逻辑）"""
    memory = get_memory()
    from src.memory.models.summary import MessageSummary

    # 1. 创建会话并添加消息
    cid = memory.start_session(title="测试摘要生成")
    mids = []
    for i in range(5):
        mid = memory.save_message(cid=cid, role="user", content=f"测试消息 {i+1}")
        mids.append(mid)

    # 2. 创建摘要
    summary = MessageSummary(
        sid="test_summary_001",
        cid=cid,
        summary_type="conversation",
        covered_mids=mids,
        start_mid=mids[0],
        end_mid=mids[-1],
        message_count=len(mids),
        summary="这是测试摘要，覆盖了 5 条测试消息",
        key_points=["要点1", "要点2"],
        entities={},
        topics=["测试"],
        parent_summary_id=None,
        child_summary_ids=[],
        can_expand=True,
        expansion_hint="",
        created_at=datetime.now().isoformat(),
        created_by="test",
    )
    memory.save_summary(summary)
    console.print("  摘要创建成功")

    # 3. 查询摘要
    fetched = memory.get_summary(summary.sid)
    assert fetched is not None, "摘要查询返回 None"
    assert fetched.summary == summary.summary, "摘要内容不匹配"
    assert fetched.message_count == len(mids), "摘要消息数不匹配"
    console.print("  摘要查询验证通过")

    # 4. 查询会话所有摘要
    all_summaries = memory.get_summaries(cid)
    assert len(all_summaries) == 1, f"期望 1 个摘要，实际 {len(all_summaries)}"
    console.print("  会话摘要列表验证通过")

    # 5. 清理
    memory._current_cid = None
    memory.delete_session(cid)


def run_test_extraction():
    """测试记忆提取（核心逻辑）"""
    memory = get_memory()
    import sqlite3

    # 1. 创建会话
    cid = memory.start_session(title="测试记忆提取")
    mid = memory.save_message(cid=cid, role="user", content="我持有贵州茅台600519，偏好低风险投资")

    # 2. 创建记忆提取记录
    extraction_data = {"preference": "低风险投资", "holdings": "600519"}
    ext_id = "test_ext_001"

    conn = sqlite3.connect(memory.db.db_path)
    conn.execute(
        """INSERT OR REPLACE INTO memory_extractions
           (extraction_id, cid, mid, intent_type, confidence,
            extracted_data, saved_to_immediate, saved_to_working,
            saved_to_longterm, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ext_id, cid, mid, "user_preference", 0.95,
            str(extraction_data), 1, 0, 0,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    console.print("  记忆提取记录保存成功")

    # 3. 验证查询
    row = conn.execute(
        "SELECT * FROM memory_extractions WHERE extraction_id = ?",
        (ext_id,),
    ).fetchone()
    conn.close()

    assert row is not None, "记忆提取记录查询返回 None"
    assert row[3] == "user_preference", f"意图类型不匹配: {row[3]}"
    console.print("  记忆提取记录查询验证通过")

    # 4. 清理
    memory._current_cid = None
    memory.delete_session(cid)


# ==================== Click 命令 ====================


@click.group()
def test():
    """测试命令 - 自动化测试 FAgent 功能"""
    pass


@test.command('message-flow')
def test_message_flow():
    """测试消息流"""
    console.print("[bold]测试消息流...[/bold]\n")
    try:
        run_test_message_flow()
        console.print("\n[green bold]消息流测试通过[/green bold]")
    except Exception as e:
        console.print(f"\n[red bold]消息流测试失败：{e}[/red bold]")
        raise


@test.command('summary-generation')
def test_summary_generation():
    """测试摘要生成"""
    console.print("[bold]测试摘要生成...[/bold]\n")
    try:
        run_test_summary_generation()
        console.print("\n[green bold]摘要生成测试通过[/green bold]")
    except Exception as e:
        console.print(f"\n[red bold]摘要生成测试失败：{e}[/red bold]")
        raise


@test.command('extraction')
def test_extraction():
    """测试记忆提取"""
    console.print("[bold]测试记忆提取...[/bold]\n")
    try:
        run_test_extraction()
        console.print("\n[green bold]记忆提取测试通过[/green bold]")
    except Exception as e:
        console.print(f"\n[red bold]记忆提取测试失败：{e}[/red bold]")
        raise


@test.command('session')
def test_session_cmd():
    """测试会话管理"""
    console.print("[bold]测试会话管理...[/bold]\n")
    try:
        run_test_session()
        console.print("\n[green bold]会话管理测试通过[/green bold]")
    except Exception as e:
        console.print(f"\n[red bold]会话管理测试失败：{e}[/red bold]")
        raise


@test.command('all')
def test_all():
    """运行所有测试"""
    console.print("[bold]运行所有测试...[/bold]\n")

    results = []

    tests = [
        ("会话管理", run_test_session),
        ("消息流", run_test_message_flow),
        ("摘要生成", run_test_summary_generation),
        ("记忆提取", run_test_extraction),
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
        status = "[green]通过[/green]" if success else "[red]失败[/red]"
        note = error if error else "-"
        table.add_row(name, status, note)

        if success:
            passed += 1
        else:
            failed += 1

    console.print(table)
    console.print(f"\n总计：{passed} 通过，{failed} 失败")

    if failed > 0:
        console.print(f"\n[red bold]{failed} 个测试失败[/red bold]")
    else:
        console.print(f"\n[green bold]所有测试通过![/green bold]")


@test.command('clean')
@click.option('--yes', '-y', is_flag=True, help='确认清理')
def test_clean(yes):
    """清理测试数据"""
    memory = get_memory()

    if not yes:
        click.confirm("确定要清理所有测试会话吗？", abort=True)

    try:
        sessions = memory.list_sessions()
        test_sessions = [s for s in sessions if '测试' in (s['title'] or '') or 'test' in (s['title'] or '').lower()]

        for session in test_sessions:
            if session['cid'] == memory.current_cid:
                continue
            memory.delete_session(session['cid'])
            console.print(f"  删除测试会话：{session['cid']}")

        console.print(f"\n[green]清理完成，共删除 {len(test_sessions)} 个测试会话[/green]")

    except Exception as e:
        console.print(f"[red]清理失败：{e}[/red]")
