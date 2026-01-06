# Frontend 模块

基于 React 的 Web 前端，提供类似 ChatGPT 的对话界面。

## 📋 开发状态

| Phase | 状态 | 说明 |
|-------|:----:|------|
| Phase 1: 项目初始化 | ✅ | Vite + React + TypeScript + Tailwind |
| Phase 2: 核心组件 | ✅ | Layout, Sidebar, ChatArea, MessageList |
| Phase 3: API 对接 | ✅ | SSE 流式处理 |
| Phase 4: 样式优化 | ⏳ | 响应式、深色模式 |

> ⏳ 待开始 | 🚧 进行中 | ✅ 已完成

---

## 🛠️ 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Node.js | 18+ | 运行环境 |
| React | 18 | UI 框架 |
| TypeScript | 5 | 类型安全 |
| Vite | 5 | 构建工具 |
| Tailwind CSS | 3 | 样式框架 |
| shadcn/ui | - | 组件库 |

---

## 📁 目录结构

```
frontend/
├── src/
│   ├── components/         # UI 组件
│   │   ├── Layout.tsx          # 整体布局
│   │   ├── Sidebar.tsx         # 左侧会话列表
│   │   ├── ChatArea.tsx        # 右侧聊天区域
│   │   ├── MessageList.tsx     # 消息列表
│   │   ├── MessageItem.tsx     # 单条消息
│   │   └── ChatInput.tsx       # 输入框
│   ├── hooks/              # 自定义 Hook
│   │   └── useChat.ts          # SSE 流式处理
│   ├── lib/                # 工具库
│   │   └── api.ts              # API 调用封装
│   ├── types/              # 类型定义
│   │   └── index.ts
│   ├── App.tsx             # 主入口
│   └── main.tsx            # 挂载点
├── public/                 # 静态资源
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
├── vite.config.ts
└── README.md               # 本文档
```
