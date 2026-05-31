# 文档总览

本目录同时包含三类内容：

- 当前有效的说明文档：描述现在仓库里可运行、可调试、可继续开发的内容。
- 设计文档：记录目标形态、接口设想和实现边界，不等同于“已经全部落地”。
- 历史报告：保留某个时间点的测试、进度或结项快照，仅供追溯，不作为当前状态依据。

## 建议优先阅读

- 根目录 [README.md](../README.md)：项目总览、启动方式、文档入口
- [backend/README.md](../backend/README.md)：Backend 运行与接口范围
- [agents/README.md](../agents/README.md)：Agents 路由、行情工具、Mock 模式
- [frontend/README.md](../frontend/README.md)：前端开发与代理配置
- [tests/README.md](../tests/README.md)：测试分层与常用命令
- [BADCASES.md](BADCASES.md)：用户实测发现的问题、根因、修复和回归验证记录

## Memory 相关

- [memory/DESIGN.md](memory/DESIGN.md)：设计基线和关键决策
- [memory/API.md](memory/API.md)：当前代码可直接使用的 Memory API
- [memory/EXAMPLES.md](memory/EXAMPLES.md)：可运行示例
- [memory/DEVELOPMENT_PLAN.md](memory/DEVELOPMENT_PLAN.md)：当前落地状态和下一步

## 数据与架构

- [CONVERSATIONAL_QUANT_AGENT_PLAN.md](CONVERSATIONAL_QUANT_AGENT_PLAN.md)：对话式量化投资经理的目标架构、阶段计划和验收场景
- [DATA_SERVICE.md](DATA_SERVICE.md)
- [MCP.md](MCP.md)
- [HISTORICAL_DATA_OPTIONS.md](HISTORICAL_DATA_OPTIONS.md)
- [FINANCIAL_DATA_CACHE_BEST_PRACTICES.md](FINANCIAL_DATA_CACHE_BEST_PRACTICES.md)

## 历史快照

以下文档保留历史记录，可能包含当时的计划状态、测试结果或阶段性结论：

- `COMPLETION_REPORT_*.md`
- `FINAL_COMPLETION_REPORT.md`
- `PROGRESS_REPORT_*.md`
- `TEST_REPORT_*.md`
- `modular_architecture_final_summary.md`
- `reports/` 下的 HTML / Markdown 报告

如果你要判断“现在仓库怎么跑、有哪些能力、哪些还没接完”，请优先看当前有效说明文档，而不是历史报告。
