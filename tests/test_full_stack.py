#!/usr/bin/env python3
"""
FAgent 全栈测试脚本

测试范围：
1. 前端 API 接口
2. 后端 API 接口
3. Agents 服务
4. 数据集缓存
5. 流式对话
"""

import httpx
import json
import time
import sys
from typing import Optional

# 服务地址
FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"
AGENTS_URL = "http://localhost:8001"

# 测试统计
stats = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
}

def log_test(name: str, status: str, details: str = ""):
    """记录测试结果"""
    emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}
    print(f"{emoji.get(status, '•')} {name}: {status}")
    if details:
        print(f"   {details}")
    
    stats["total"] += 1
    if status == "PASS":
        stats["passed"] += 1
    elif status == "FAIL":
        stats["failed"] += 1
    elif status == "SKIP":
        stats["skipped"] += 1

# ==================== 健康检查 ====================

def test_service_health():
    """测试服务健康状态"""
    print("\n" + "="*60)
    print("📊 服务健康检查")
    print("="*60)
    
    # 前端
    try:
        response = httpx.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            log_test("前端服务", "PASS", f"{FRONTEND_URL}")
        else:
            log_test("前端服务", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("前端服务", "FAIL", str(e))
    
    # 后端 API
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200 and response.json().get("status") == "healthy":
            log_test("后端 API", "PASS", f"{BACKEND_URL}")
        else:
            log_test("后端 API", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("后端 API", "FAIL", str(e))
    
    # Agents 服务
    try:
        response = httpx.get(f"{AGENTS_URL}/agent/chat/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            log_test("Agents 服务", "PASS", f"{AGENTS_URL} | 模型数：{len(models)}")
        else:
            log_test("Agents 服务", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("Agents 服务", "FAIL", str(e))

# ==================== 后端 API 测试 ====================

def test_backend_api():
    """测试后端 API"""
    print("\n" + "="*60)
    print("🔧 后端 API 测试")
    print("="*60)
    
    # 创建会话
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/chat/session/create",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            cid = data.get("cid")
            log_test("创建会话", "PASS", f"cid={cid}")
            return cid
        else:
            log_test("创建会话", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("创建会话", "FAIL", str(e))
    
    return None

def test_session_operations(cid: Optional[int]):
    """测试会话操作"""
    print("\n" + "="*60)
    print("📝 会话操作测试")
    print("="*60)
    
    if not cid:
        log_test("获取会话列表", "SKIP", "无有效会话 ID")
        return
    
    # 获取会话列表
    try:
        response = httpx.get(f"{BACKEND_URL}/api/chat/conversations", timeout=10)
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            log_test("获取会话列表", "PASS", f"总数：{count}")
        else:
            log_test("获取会话列表", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("获取会话列表", "FAIL", str(e))
    
    # 获取会话消息
    try:
        response = httpx.get(f"{BACKEND_URL}/api/chat/conversation/{cid}/messages", timeout=10)
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            log_test("获取会话消息", "PASS", f"消息数：{count}")
        else:
            log_test("获取会话消息", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("获取会话消息", "FAIL", str(e))
    
    # 重命名会话
    try:
        response = httpx.patch(
            f"{BACKEND_URL}/api/chat/conversation/{cid}",
            json={"title": "测试会话"},
            timeout=10
        )
        if response.status_code == 200:
            log_test("重命名会话", "PASS", f"cid={cid}")
        else:
            log_test("重命名会话", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("重命名会话", "FAIL", str(e))

def test_chat_stream(cid: Optional[int]):
    """测试流式对话"""
    print("\n" + "="*60)
    print("💬 流式对话测试")
    print("="*60)
    
    if not cid:
        log_test("流式对话", "SKIP", "无有效会话 ID")
        return
    
    # 发送消息
    try:
        print("发送测试消息...")
        with httpx.stream(
            "POST",
            f"{BACKEND_URL}/api/chat/send/stream",
            json={
                "cid": cid,
                "user_message": "你好，请简单介绍一下你自己",
                "model": "mimo-v2-flash",
            },
            timeout=60
        ) as response:
            if response.status_code == 200:
                chunks = []
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "content" in data:
                                chunks.append(data["content"])
                                print(data["content"], end="", flush=True)
                        except:
                            pass
                
                print()  # 换行
                full_response = "".join(chunks)
                if len(full_response) > 0:
                    log_test("流式对话", "PASS", f"响应长度：{len(full_response)}")
                else:
                    log_test("流式对话", "FAIL", "无响应内容")
            else:
                log_test("流式对话", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("流式对话", "FAIL", str(e))

# ==================== Agents 服务测试 ====================

def test_agents_service():
    """测试 Agents 服务"""
    print("\n" + "="*60)
    print("🤖 Agents 服务测试")
    print("="*60)
    
    # 获取可用模型
    try:
        response = httpx.get(f"{AGENTS_URL}/agent/chat/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            default = data.get("default", "")
            log_test("获取模型列表", "PASS", f"默认模型：{default}")
        else:
            log_test("获取模型列表", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("获取模型列表", "FAIL", str(e))
    
    # 测试简单对话（非流式）
    try:
        response = httpx.post(
            f"{AGENTS_URL}/agent/chat/completion",
            json={
                "cid": 999,
                "message_id": 999,
                "user_message": "你好",
                "history_limit": 10,
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            log_test("简单对话", "PASS", f"响应长度：{len(content)}")
        else:
            log_test("简单对话", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("简单对话", "FAIL", str(e))

# ==================== 数据集缓存测试 ====================

def test_dataset_cache():
    """测试数据集缓存"""
    print("\n" + "="*60)
    print("💾 数据集缓存测试")
    print("="*60)
    
    # 测试缓存统计
    try:
        response = httpx.get(f"{AGENTS_URL}/market/cache/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            log_test("缓存统计", "PASS", json.dumps(data, indent=2))
        else:
            log_test("缓存统计", "SKIP", f"Status: {response.status_code} (可能未实现)")
    except Exception as e:
        log_test("缓存统计", "SKIP", str(e))
    
    # 测试 A 股行情（会触发缓存）
    try:
        print("测试 A 股行情查询（首次会缓存）...")
        start = time.time()
        response = httpx.get(
            f"{AGENTS_URL}/market/quote/a_share/000001",
            timeout=60
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            log_test("A 股行情（首次）", "PASS", f"耗时：{duration:.2f}s | 股票：{data.get('name', 'N/A')}")
        else:
            log_test("A 股行情（首次）", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("A 股行情（首次）", "FAIL", str(e))
    
    # 测试缓存命中
    try:
        print("测试 A 股行情查询（应从缓存获取）...")
        start = time.time()
        response = httpx.get(
            f"{AGENTS_URL}/market/quote/a_share/000001",
            timeout=30
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            log_test("A 股行情（缓存）", "PASS", f"耗时：{duration:.2f}s ⚡")
        else:
            log_test("A 股行情（缓存）", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("A 股行情（缓存）", "FAIL", str(e))

# ==================== 主测试流程 ====================

def main():
    """主测试流程"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "FAgent 全栈测试" + " "*20 + "║")
    print("╚" + "="*58 + "╝")
    print()
    
    # 1. 健康检查
    test_service_health()
    
    # 2. 后端 API 测试
    cid = test_backend_api()
    
    # 3. 会话操作
    test_session_operations(cid)
    
    # 4. 流式对话
    test_chat_stream(cid)
    
    # 5. Agents 服务
    test_agents_service()
    
    # 6. 数据集缓存
    test_dataset_cache()
    
    # 统计结果
    print("\n" + "="*60)
    print("📊 测试结果统计")
    print("="*60)
    print(f"总测试数：{stats['total']}")
    print(f"✅ 通过：{stats['passed']}")
    print(f"❌ 失败：{stats['failed']}")
    print(f"⏭️  跳过：{stats['skipped']}")
    print()
    
    if stats['failed'] == 0:
        print("🎉 所有测试通过！")
        return 0
    else:
        print(f"⚠️  有 {stats['failed']} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
