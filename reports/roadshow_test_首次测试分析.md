# 路演多轮对话测试 - 首次测试分析报告

**测试时间**: 2026-03-20 09:27-09:28  
**测试场景数**: 8 个  
**测试结果**: ❌ 全部失败
**说明**: 这是历史问题分析快照，当前仓库的标准启动方式请以根目录 `README.md` 为准。

---

## 📊 测试结果

| 指标 | 结果 |
|------|------|
| 总场景数 | 8 个 |
| 通过场景 | 0 个 |
| 失败场景 | 8 个 |
| 可路演示例 | 0 个 |

---

## ❌ 失败原因分析

### 根本原因

**Agents 服务未运行** (端口 8001)

Backend API 在 `/api/chat/send/stream` 接口调用 LLM 时需要转发请求到 Agents 服务（端口 8001），但该服务未启动，导致：
- HTTP 502 Bad Gateway 错误
- 所有对话请求返回空内容
- 测试场景全部失败

### 错误日志

```
2026-03-20 09:28:04.498 | ERROR | backend.api.chat:generate_conversation_title:83 | 
[cid=7 mid=37 rid=eb2981b0] [SESSION] 标题生成失败 | 
原因=Server error '502 Bad Gateway' for url 'http://localhost:8001/agent/summary/generate'
```

---

## ✅ 解决方案

### 方案 1: 启动 Agents 服务（推荐）

```bash
# 1. 检查 Agents 服务配置
cd <repo-root>
ls -la agents/

# 2. 启动 Agents 服务
python3 -m uvicorn agents.api.main:app --reload --port 8001

# 3. 验证服务启动
curl http://localhost:8001/health
```

### 方案 2: 使用 Mock 模式测试

如果 Agents 服务暂时无法启动，可以修改测试框架使用 Mock 回复：

```python
# 在 tests/test_roadshow_multi_turn.py 中添加 Mock 模式
class MockMultiTurnTester(MultiTurnTester):
    def send_message(self, user_message: str):
        # 返回预设的 Mock 回复
        return "这是 Mock 回复", 1000, True, None
```

### 方案 3: 测试 Backend API 连通性（当前可用）

虽然 Agents 未运行，但 Backend 基础功能正常：
- ✅ Backend 服务启动成功（端口 8000）
- ✅ 健康检查接口正常
- ✅ 会话创建接口正常
- ❌ 对话接口需要 Agents 服务

---

## 📋 下一步行动

### 立即执行

1. **启动 Agents 服务**
   ```bash
   cd <repo-root>
   python3 -m uvicorn agents.api.main:app --reload --port 8001
   ```

2. **验证服务运行**
   ```bash
   curl http://localhost:8001/health
   ```

3. **重新运行测试**
   ```bash
   ./scripts/run_roadshow_test.sh
   ```

### 如果 Agents 服务无法启动

1. **检查 Agents 服务依赖**
   ```bash
   cd <repo-root>
   ls -la agents/
   cat agents/README.md 2>/dev/null || echo "无 README"
   ```

2. **检查环境变量**
   ```bash
   cat .env | grep -i agent
   ```

3. **查看 Agents 服务日志**
   ```bash
   tail -50 logs/agents/*.log 2>/dev/null
   ```

---

## 🎯 测试框架验证

虽然测试失败，但测试框架本身工作正常：

### ✅ 已验证功能

1. **测试场景加载** - 成功加载 8 个场景
2. **会话创建** - 成功创建多个会话（cid=3 到 cid=11）
3. **消息发送** - 成功调用 API（虽然返回空）
4. **报告生成** - 成功生成 30KB HTML 报告

### ⏳ 待验证功能（需要 Agents 服务）

1. **内容质量评估**
2. **连贯性评分**
3. **对话示例筛选**

---

## 📊 预期测试结果（Agents 服务正常后）

### 乐观估计

| 场景类型 | 预期通过率 | 可路演示例 |
|---------|-----------|-----------|
| 业务场景 (RS001-RS005) | 80-90% | 3-4 个 |
| 闲聊场景 (RS000,RS006-RS008) | 60-80% | 2-3 个 |
| **总计** | **70-85%** | **5-7 个** |

### 保守估计

| 场景类型 | 预期通过率 | 可路演示例 |
|---------|-----------|-----------|
| 业务场景 (RS001-RS005) | 60-80% | 2-3 个 |
| 闲聊场景 (RS000,RS006-RS008) | 40-60% | 1-2 个 |
| **总计** | **50-70%** | **3-5 个** |

---

## 🔧 快速诊断脚本

创建一个快速诊断脚本检查所有服务：

```bash
#!/bin/bash
# diagnose_services.sh

echo "================================================"
echo "🔍 FAgent 服务诊断工具"
echo "================================================"

# 检查 Backend 服务
echo -e "\n1. Backend 服务 (端口 8000):"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ 运行中"
    curl -s http://localhost:8000/health | python3 -m json.tool
else
    echo "   ❌ 未运行"
fi

# 检查 Agents 服务
echo -e "\n2. Agents 服务 (端口 8001):"
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "   ✅ 运行中"
    curl -s http://localhost:8001/health | python3 -m json.tool
else
    echo "   ❌ 未运行"
fi

# 检查端口占用
echo -e "\n3. 端口占用情况:"
echo "   端口 8000: $(lsof -ti:8000 >/dev/null 2>&1 && echo '已占用' || echo '空闲')"
echo "   端口 8001: $(lsof -ti:8001 >/dev/null 2>&1 && echo '已占用' || echo '空闲')"

echo -e "\n================================================"
```

---

## 📞 联系支持

如需帮助，请检查：

1. `agents/README.md` - Agents 服务文档
2. `logs/agents/` - Agents 服务日志
3. `.env` - 环境变量配置

---

**结论**: 测试框架正常，需要启动 Agents 服务后重新测试！

**下一步**: 启动 Agents 服务 → 重新运行测试 → 查看结果
