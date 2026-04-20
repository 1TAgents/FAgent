#!/usr/bin/env python3
"""
Memory 三层记忆层测试
"""

import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from memory.layers import ImmediateMemory, WorkingMemory, LongTermMemory
from memory.layers.working import Task


def test_immediate_memory():
    """测试 L1 瞬时记忆"""
    mem = ImmediateMemory()
    
    # 添加对话
    mem.add_turn("user", "测试消息")
    mem.add_turn("assistant", "回复")
    
    assert len(mem.conversation_history) == 2
    assert mem.current_turn == "回复"
    
    # 添加工具调用
    mem.add_tool_call("market_data", {"symbol": "600519"})
    assert len(mem.tool_calls) == 1
    
    # 获取最近对话
    recent = mem.get_recent_turns(limit=5)
    assert len(recent) == 2
    
    print("✓ L1 瞬时记忆")


def test_working_memory():
    """测试 L2 工作记忆"""
    with tempfile.TemporaryDirectory() as tmpdir:
        wm = WorkingMemory(f"{tmpdir}/working.db")
        
        # 创建任务
        task = Task(
            task_id="task_001",
            task_type="analysis",
            title="测试任务",
            context={"symbol": "600519"},
            status="active",
            decision_chain=[],
            todo_queue=[{"action": "test", "done": False}],
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=24)).isoformat()
        )
        
        task_id = wm.create_task(task)
        assert task_id == "task_001"
        
        # 获取任务
        retrieved = wm.get_task(task_id)
        assert retrieved.title == "测试任务"
        
        # 追加决策
        wm.append_decision(task_id, {"type": "test", "content": "决策 1"})
        task = wm.get_task(task_id)
        assert len(task.decision_chain) == 1
        
        # 获取活跃任务
        tasks = wm.get_active_tasks()
        assert len(tasks) == 1
        
        print("✓ L2 工作记忆")


def test_longterm_memory():
    """测试 L3 长期记忆"""
    with tempfile.TemporaryDirectory() as tmpdir:
        ltm = LongTermMemory(tmpdir)
        
        # 更新用户画像
        profile = {
            "user_id": "default",
            "risk_tolerance": "medium",
            "preferred_holding_period": "long",
            "stop_loss_ratio": 0.05
        }
        ltm.update_profile(profile)
        
        # 获取画像
        retrieved = ltm.get_profile()
        assert retrieved["risk_tolerance"] == "medium"
        assert retrieved["preferred_holding_period"] == "long"
        
        # 记录交易
        trade = {
            "trade_id": "trade_001",
            "symbol": "600519",
            "trade_type": "buy",
            "quantity": 100,
            "price": 1800.0,
            "amount": 180000.0,
            "executed_at": datetime.now().isoformat(),
            "reason": "测试交易"
        }
        ltm.record_trade(trade)
        
        # 获取交易
        trades = ltm.get_trades("600519")
        assert len(trades) == 1
        assert trades[0]["symbol"] == "600519"
        
        print("✓ L3 长期记忆")


def main():
    """运行所有测试"""
    print("运行 Memory 三层记忆层测试...\n")
    
    from datetime import datetime, timedelta
    
    tests = [
        test_immediate_memory,
        test_working_memory,
        test_longterm_memory,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} 失败：{e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 错误：{e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"测试完成：{passed} 通过，{failed} 失败")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("✓ 所有三层记忆层测试通过!")
        sys.exit(0)


if __name__ == '__main__':
    main()
