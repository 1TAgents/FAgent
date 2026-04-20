# FAgent - Android 应用实现指南

> 状态：未来规划 / 参考草案
>
> 当前仓库的主交付仍是 Web 前端，运行说明请优先参考 `frontend/README.md`。
> 本文档保留 Android 方向的设计思路，但不代表当前仓库已经进入 Android 实装阶段。

本文档旨在为未来可能的 FAgent Android 应用开发提供技术参考，以确保后续扩展与项目总体设计保持一致。

## 1. 项目架构与技术选型

为了构建一个健壮、可维护且可扩展的应用，我们推荐采用业界主流的架构模式和库。

### 1.1. 架构模式

推荐采用 **MVVM (Model-View-ViewModel)** 架构模式，并结合 Google 推荐的[《应用架构指南》](https://developer.android.com/topic/architecture)。

- **View (UI Layer)**: 使用 **Jetpack Compose** 构建声明式 UI。Activity/Fragment 作为屏幕的容器，具体的 UI 元素和逻辑由 Composable 函数负责。
- **ViewModel (ViewModel Layer)**: 负责存储和管理与 UI 相关的数据，处理 UI 逻辑，并通过 `StateFlow` 或 `LiveData` 将数据暴露给 UI 层。
- **Model (Data Layer)**: 由 **Repository** 组成，负责统一处理数据来源（网络、本地数据库），为 ViewModel 提供干净的数据接口。

### 1.2. 模块划分

根据 `README.md` 中的项目结构，各模块职责如下：

- `app`: 主应用模块，负责组装所有功能模块，包含应用的入口（Activity）、导航图以及依赖注入的顶层配置。
- `core`: 核心功能模块，提供整个应用通用的工具类、扩展函数、基础组件（如网络请求封装、数据库实例）。
- `ui`: 通用 UI 组件模块，包含应用内可复用的 UI 元素，如自定义按钮、图表组件、对话框等，遵循 Material Design 风格。
- `data`: 数据层模块，包含所有的数据源（ApiService、DAO）、Repository 实现以及数据模型（DTOs, Entities）。

### 1.3. 关键技术栈与第三方库

- **UI**:
  - `Jetpack Compose`: 用于构建整个应用的 UI。
  - `Compose Navigation`: 管理应用内的屏幕跳转。
  - `Material Design 3`: 提供设计系统和组件。
- **异步编程**:
  - `Kotlin Coroutines` & `Flow`: 处理所有异步任务，如网络请求、数据库操作。
- **依赖注入**:
  - `Hilt`: 用于在整个应用中管理依赖关系。
- **网络**:
  - `Retrofit`: 用于处理 RESTful API 请求。
  - `OkHttp`: 作为 Retrofit 的 HTTP 客户端，并用于实现 WebSocket 通信。
  - `Gson` / `kotlinx.serialization`: 用于 JSON 解析。
- **数据持久化**:
  - `Room`: 用于缓存行情数据、用户策略等。
  - `DataStore`: 用于存储用户偏好设置。
  - `EncryptedSharedPreferences`: 用于安全地存储敏感信息，如交易平台的 API Key。
- **图表**:
  - `MPAndroidChart` 或 Compose-native 的图表库（如 `Vico`）：用于展示行情和回测结果。

## 2. 功能模块实现步骤

### 2.1. 对话式交互

这是应用的核心，用户通过对话与 FAgent 交互。

1.  **UI 层 (`ui` / `app` 模块)**
    -   创建一个 `ChatScreen` Composable 函数。
    -   使用 `LazyColumn` 展示对话消息列表。
    -   为不同来源（用户/FAgent）和内容（文本/图表/策略卡片）创建不同的 Composable `ChatItem`。
    -   底部使用 `TextField` 作为用户输入框。

2.  **ViewModel**
    -   创建一个 `ChatViewModel`。
    -   使用 `StateFlow<List<Message>>` 管理对话消息列表。
    -   提供一个 `sendMessage(text: String)` 函数，该函数会：
        -   将用户消息添加到 UI 状态中。
        -   调用 `Repository` 将消息发送到后端。
        -   接收到后端响应后，将 FAgent 的消息也添加到 UI 状态中。

3.  **Data 层 (`data` 模块)**
    -   在 `Repository` 中创建 `postMessage(message: String)` 函数。
    -   使用 Retrofit 定义 `ApiService`，包含一个指向后端 NLP/LLM 服务的接口。
    -   处理后端返回的不同类型的数据（纯文本、行情数据、策略对象等），并转换为应用内的数据模型。

### 2.2. 行情查询

1.  **UI 层**
    -   在对话消息中，为行情数据设计一个专用的卡片式 `Composable`，清晰地展示价格、涨跌幅等。
    -   （可选）创建一个 `StockDetailScreen`，用于展示更详细的 K 线图和技术指标。使用 `Compose Navigation` 从对话流中跳转到此页面。

2.  **Data 层**
    -   **REST API**: 在 `ApiService` 中定义获取股票基本信息、历史 K 线数据的接口。
    -   **WebSocket**:
        -   使用 `OkHttp` 的 `WebSocketListener` 来建立与后端服务的长连接，接收实时的行情推送。
        -   在 `Repository` 中管理 WebSocket 的生命周期（连接、断开、重连）。
        -   将接收到的实时数据通过 `SharedFlow` 或 `StateFlow` 暴露给 ViewModel。
    -   **缓存**:
        -   使用 `Room` 数据库创建 `StockInfo` 和 `KlineData` 等实体。
        -   在 `Repository` 中实现缓存策略：优先从网络获取数据，成功后更新到 Room；网络失败则从 Room 读取缓存数据。

### 2.3. 策略制定与回测

1.  **UI 层**
    -   **策略创建**: 主要通过对话完成。当后端识别出策略创建意图并返回策略详情后，在对话中以卡片形式展示该策略。
    -   **回测触发**: 在策略卡片上提供一个 "执行回测" 按钮。
    -   **回测报告**: 创建一个 `BacktestReportScreen`，用于可视化回测结果。
        -   使用图表库绘制收益曲线和最大回撤图。
        -   使用 `LazyColumn` 或 `Table` 展示关键性能指标（收益率、夏普比率等）。

2.  **Data 层**
    -   在 `ApiService` 中定义相关接口：
        -   `POST /strategies`: 创建新策略。
        -   `POST /backtest`: 提交回测任务。后端可能是异步处理，可以返回一个任务 ID。
        -   `GET /backtest/results/{taskId}`: 使用任务 ID 轮询或通过 WebSocket 接收回测结果。
    -   在 `Repository` 中封装这些调用，并处理异步回测的逻辑。

### 2.4. 自动化交易

1.  **UI 层**
    -   在策略详情页或管理页，提供一个开关（`Switch`）来“启用/禁用”自动化交易。
    -   创建一个 `TradingDashboardScreen`，实时展示已启用策略的运行状态、持仓、收益等。

2.  **Data 层**
    -   **安全**:
        -   用户的交易 API Key **必须** 使用 `EncryptedSharedPreferences` 进行加密存储。
        -   在进行交易相关的网络请求时，从加密存储中读取密钥。
    -   **通信**:
        -   在 `ApiService` 中定义 `POST /trading/start` 和 `POST /trading/stop` 等接口。
        -   通过 WebSocket 接收交易执行的实时通知（如下单成功、成交回报、风险警告等）。
    -   `Repository` 负责将这些实时状态通过 `Flow` 传递给 `ViewModel`。


## 3. 开发计划建议

与 `README.md` 中的开发计划对齐，Android 端的具体实施步骤如下：

### Phase 1: 基础功能
1.  **项目初始化**: 搭建 Hilt、Compose、Retrofit 和 Room 的基本环境。
2.  **对话界面**: 完成 `ChatScreen` 的基础 UI 布局。
3.  **网络连接**: 实现 `ChatViewModel` 和 `Repository`，能够将用户输入发送到后端，并接收文本响应显示在界面上。
4.  **基础行情**: 实现基础行情查询的 API 调用，并在对话中以文本形式展示结果。

### Phase 2: 核心功能
1.  **策略回测**: 实现回测相关的 API 调用和 `BacktestReportScreen` 的 UI，包括图表集成。
2.  **数据缓存**: 为行情数据和 K 线数据添加 Room 缓存逻辑。
3.  **策略管理**: 创建一个简单的列表页面来管理用户已创建的策略。

### Phase 3: 交易功能
1.  **安全存储**: 集成 `EncryptedSharedPreferences` 用于存储 API Key。
2.  **交易接口**: 实现启用/禁用策略的 API 调用。
3.  **实时监控**: 建立 WebSocket 连接以接收交易状态，并构建 `TradingDashboardScreen`。

### Phase 4: 优化与扩展
1.  **UI/UX 优化**: 打磨动画效果、加载状态、错误提示等用户体验细节。
2.  **性能优化**: 分析并优化应用启动速度、内存使用和网络请求效率。
3.  **代码健壮性**: 完善单元测试和 UI 测试。

---
**注意**：本文档是一个指导性框架，具体实现细节可能需要根据后端 API 的最终设计进行调整。
