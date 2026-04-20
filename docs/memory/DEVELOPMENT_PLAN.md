# FAgent Memory 开发状态

> 更新日期：2026-04-20
> 状态：基础存储与查询已落地，自动提取和 LLM 集成仍在继续

## 已落地

### 核心存储

- `src/memory/ids.py`
- `src/memory/models/`
- `src/memory/storage/database.py`
- `src/memory/manager.py`

当前已经可以：

- 创建会话
- 保存 / 查询原始消息
- 保存 / 查询摘要
- 保存 / 查询工具响应

### 查询 API

- `src/memory/api.py`

当前已经支持：

- 会话概览
- 消息列表
- 单条消息详情
- 工具响应详情
- 摘要展开
- 关键词搜索

### 三层记忆原型

- `layers/immediate.py`
- `layers/working.py`
- `layers/longterm.py`

这些类已经存在并可单独使用，但尚未自动接入 Backend / Agents。

### 测试

- `tests/memory/`
- `tests/cli/`

## 部分完成

### CLI

已完成：

- CLI 框架
- `session` 命令组

仍需补齐：

- `message` 命令真实读写
- `memory` 命令完整接入 `MemoryAPI`
- `test` 命令与真实能力对齐

### 设计与代码对齐

已完成：

- 设计文档、API 文档、示例文档已开始按真实代码收敛

仍需补齐：

- Manager 对三层记忆的统一入口
- 更清晰的对外稳定接口

## 尚未开始或未完成

- 自动摘要生成
- 自动记忆提取
- Context Builder
- LLM 主动调用 Memory Tool
- Experience Memory
- Backend / Agents 对 Memory 的真实接线

## 推荐下一步

1. 给 `MemoryManager` 增加稳定的 `api` 入口，减少调用方样板代码。
2. 把 CLI 的 `message` / `memory` 命令补成真实实现。
3. 明确三层记忆与主聊天链路的接入点。
4. 为自动摘要和自动提取补最小闭环。
5. 在 Backend / Agents 中先接入只读查询能力，再逐步接入写入。

## 当前判断标准

如果你在看“Memory 现在能不能用”，建议按下面理解：

- 能用：本地存储、查询、测试、独立实验
- 不能直接假设已完成：与主聊天链路的自动联动、经验演化、LLM 动态检索
