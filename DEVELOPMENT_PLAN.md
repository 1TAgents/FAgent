# FAgent 开发路线图

> 更新日期：2026-05-15

本文档记录 FAgent 基于 10 维度分析的改进进展和下一步方向。

## 10 维度评估（当前状态）

| # | 维度 | 状态 | 说明 |
|---|------|------|------|
| 1 | 产品定位与入口 | ✅ 清晰 | Web Chat (SPA) + Backend API + Agents Service，三层架构明确 |
| 2 | Runtime 主循环 | ✅ 已统一 | ReActAgentLoop + ReActRouter 为主链路，旧 SubAgent 路径保持兼容 |
| 3 | Message/Session/State | ✅ 已落地 | Session 状态机、SQLite 存储、历史隔离 |
| 4 | Context 构造与压缩 | ✅ 已落地 | Token 预算管理、上下文压缩、tool schema 注入 |
| 5 | Memory 系统 | ✅ 已接入 | 记忆召回已注入 ReActRouter 系统提示，防重复注入 |
| 6 | Tool/MCP/Skill | ✅ 已完善 | 11 个工具分 3 类注册，按路由分配工具集 |
| 7 | Subagent/Orchestration | ✅ ReAct 化 | 各领域通过 ReAct Loop 自主调用工具 |
| 8 | Sandbox/Permission/Security | ⚠️ 进行中 | 工具权限系统已落地，API 限流已接入 |
| 9 | Model/Provider/Protocol | ✅ 已增强 | 多提供商注册 + 跨提供商回退链 |
| 10 | Persistence/Observability | ⚠️ 需完善 | Trace 已保存，缺少回放 UI 和成本统计 |

## 本次改进（2026-05-09）

### 已完成

| 改进 | 维度 | 说明 |
|------|------|------|
| 回测工具接入 ReAct | 6 (Tool) | `list_strategies`, `get_strategy_info`, `run_backtest`, `optimize_backtest` 4 个工具 |
| 交易工具接入 ReAct | 6 (Tool) | `place_order`, `cancel_order`, `check_positions` 3 个工具 |
| 路由工具分配 | 6 (Tool) | STRATEGY/BACKTEST/TRADE 路由现在都有对应工具集 |
| Memory 接入主链路 | 5 (Memory) | ReActRouter 召回记忆并注入系统提示，ReActLoop 防重复 |
| 模型回退链 | 9 (Provider) | 主模型失败自动回退到其他提供商的模型 |
| API 限流 | 8 (Security) | 滑动窗口限流中间件，chat 30/min, auth 10/min |
| CLI 命令完整实现 | 10 (CLI) | `message` (send/list/show/search)、`memory` (5级披露API)、`test` (4项断言测试)、current_cid 跨调用持久化 |
| CLI send 命令 | 10 (CLI) | `fagent send "消息"` 通过后端 API 走完整链路，支持流式/非流式、模型选择、自动创建 session、本地消息存储 |
| 冒烟测试 | 10 (Testing) | 8个端到端测试覆盖工具注册/ReAct Loop/Trace/Memory/Prompt/Session/CLI/Observability |
| 旧 API 端点下线 | 2 (Runtime) | `/api/chat/send` 从 `/agent/chat/completion` 迁移到 `/agent/chat/router/completion` |
| CLI 安全诊断 | 8 (Security) / 10 (Observability) | `fagent doctor security-scan` 扫描本机路径、API key、token、私钥等高风险内容；支持 staged 扫描并接入 pre-commit，且不输出敏感值 |

### 下一步

无（所有已规划项已完成）。

## 备注

- Android 文档保留为未来规划，不是当前交付目标。
- 历史测试/完成报告继续保留，但不再作为当前状态依据。
