# FAgent

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android-green.svg)](https://www.android.com/)

> 一款基于对话式交互的智能股票交易助手 Android 应用

FAgent 是一款创新的 Android 应用，通过自然语言对话的方式帮助用户查询股市行情、制定交易策略、进行策略回测，并支持自动化交易执行。

## ✨ 功能特性

### 🗣️ 对话式交互
- **自然语言查询**：通过对话方式查询股票行情、技术指标等信息
- **智能理解**：理解用户的交易意图和策略需求

### 📊 行情查询
- 实时股票行情查询
- 技术指标分析
- 市场数据可视化

### 🎯 策略制定
- **对话式策略构建**：通过对话描述交易策略
- **策略模板库**：提供常用策略模板
- **策略编辑**：可视化策略编辑器

### 📈 策略回测
- **历史数据回测**：基于历史数据验证策略有效性
- **回测报告**：详细的回测结果分析和可视化
- **性能指标**：收益率、夏普比率、最大回撤等关键指标

### 🤖 自动化交易
- **策略执行**：选择认可的策略进行自动化交易
- **风险控制**：内置风险管理和止损机制
- **实时监控**：交易执行状态实时监控

## 🛠️ 技术栈

### 前端
- **Android Native Development**
- Kotlin / Java
- Material Design

### 后端服务
- Python (策略回测引擎)
- FastAPI (Web 框架)
- Server-Sent Events (SSE) - 流式输出
- RESTful API - 非流式接口
- LangGraph + LangChain - 多智能体框架

> 📖 详细的架构文档请查看 [backend/docs/ARCHITECTURE.md](backend/docs/ARCHITECTURE.md)

### AI/ML
- 大语言模型 (LLM) 集成
- 自然语言处理 (NLP)
- 策略优化算法

### 数据源
- 股票行情 API
- 历史数据存储

## 📁 项目结构

```
FAgent/
├── backend/                # 后端服务（存储 + 业务）
│   ├── api/                # FastAPI 接口
│   ├── core/               # 核心组件（日志、上下文）
│   ├── services/           # 业务服务（会话、存储）
│   └── docs/               # 后端文档
│       ├── API_USAGE.md    # API 使用文档
│       ├── ARCHITECTURE.md # 架构文档
│       └── DEBUG.md        # 调试指南
├── agents/                 # 智能体服务（LLM 调用）
│   ├── api/                # FastAPI 接口
│   ├── core/               # System Prompt 配置
│   └── services/           # LLM 服务、Chat Agent
├── tests/                  # 测试代码
│   └── test_multi_turn.py  # 多轮对话测试
├── docs/                   # 项目文档
├── frontend/               # 前端应用（Android）
└── README.md               # 项目说明文档
```

## 🚀 快速开始

### 环境要求

- Python 3.12（后端服务）
- Android Studio Arctic Fox+（Android 开发，待开发）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone git@github-personal:doraemon235/FAgent.git
   cd FAgent
   ```

2. **配置 Python 虚拟环境**
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r backend/requirements.txt
   pip install -r tests/requirements.txt
   ```

4. **配置环境变量**

   在项目根目录创建 `.env` 文件：
   ```bash
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   openrounter_p=your_api_key
   LLM_MODEL=xiaomi/mimo-v2-flash:free
   ```

5. **启动服务**
   ```bash
   # 终端 1：启动后端服务（存储 + 业务）
   uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

   # 终端 2：启动 Agents 服务（LLM 调用）
   uvicorn agents.api.main:app --reload --host 0.0.0.0 --port 8001
   ```

6. **访问 API 文档**
   - Backend: http://localhost:8000/docs
   - Agents: http://localhost:8001/docs

## 📖 使用说明

### 查询行情
```
用户: "查询一下苹果公司的股票价格"
FAgent: "AAPL 当前价格为 $XXX，今日涨幅 X%..."
```

### 制定策略
```
用户: "我想制定一个简单的均线策略，当5日均线上穿20日均线时买入"
FAgent: "已为您创建策略，策略参数如下..."
```

### 回测策略
```
用户: "回测一下这个策略在过去一年的表现"
FAgent: "回测完成，总收益率 X%，最大回撤 Y%..."
```

### 自动化交易
```
用户: "启用这个策略进行自动化交易"
FAgent: "策略已启用，将自动执行交易..."
```

## 🔒 安全说明

- ⚠️ **风险提示**：股票交易存在风险，请谨慎使用自动化交易功能
- 🔐 **数据安全**：所有敏感信息均加密存储
- 🛡️ **权限管理**：应用仅请求必要的系统权限

## 📝 开发计划

### Phase 1: 后端基础 ✅
- [x] 项目初始化
- [x] FastAPI + SSE 流式接口
- [x] 会话管理（多轮对话）
- [x] 消息持久化（SQLite）
- [x] 请求日志追踪（rid/cid）
- [x] 三层架构拆分（Frontend → Backend → Agents）
- [x] System Prompt 动态管理（不存库）

### Phase 2: 多智能体系统
- [ ] LangGraph 工作流集成
- [ ] 多智能体协作
- [ ] 长期记忆

### Phase 3: 核心功能
- [ ] 行情查询 API
- [ ] 策略回测引擎
- [ ] 交易接口集成

### Phase 4: Android 应用
- [ ] 对话式交互界面
- [ ] UI/UX 设计

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范
- 遵循项目的代码风格
- 添加必要的注释和文档
- 确保代码通过测试

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📧 联系方式

- 项目维护者: [@doraemon235](https://github.com/doraemon235)
- 问题反馈: [Issues](https://github.com/doraemon235/FAgent/issues)

## 🙏 致谢

感谢所有为本项目做出贡献的开发者和用户！

---

**注意**：本项目仍在积极开发中，功能可能随时更新。使用前请查看最新版本说明。
