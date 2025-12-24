# Frontend 模块

基于 React 的 Web 前端，提供类似 ChatGPT 的对话界面。

## 📋 开发状态

| Phase | 状态 | 说明 |
|-------|:----:|------|
| Phase 1: 项目初始化 | ⏳ | Vite + React + TypeScript + Tailwind |
| Phase 2: 核心组件 | ⏳ | Layout, Sidebar, ChatArea, MessageList |
| Phase 3: API 对接 | ⏳ | SSE 流式处理 |
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

---

## 🎨 界面设计

### 布局结构（参考 ChatGPT）

```
┌───────────────┬─────────────────────────────────────────┐
│ [+ 新聊天]    │                                         │
├───────────────┤   👤 用户消息                           │
│               │                                         │
│  ○ 会话 1     │   🤖 AI 回复（支持流式输出）            │
│  ● 会话 2     │                                         │
│  ○ 会话 3     │   👤 用户消息                           │
│               │                                         │
│               │   🤖 █ (输入中...)                      │
│               │                                         │
│               │                                         │
│               ├─────────────────────────────────────────┤
│  [用户信息]   │  [请输入消息...]              [发送 ➤]  │
└───────────────┴─────────────────────────────────────────┘
    240px                      flex-1
```

**左侧边栏：**
- 顶部：新建聊天按钮
- 中间：会话列表（可滚动）
- 底部：用户信息/设置（可选）

**右侧主区域：**
- 顶部：当前会话标题（可选）
- 中间：消息列表（可滚动）
- 底部：输入框 + 发送按钮

### 组件层级

```
App
└── Layout
    ├── Sidebar
    │   ├── NewChatButton
    │   └── SessionList
    │       └── SessionItem (多个)
    └── ChatArea
        ├── MessageList
        │   └── MessageItem (多个)
        └── ChatInput
```

---

## 🔌 API 对接

### 后端接口

| 接口 | 方法 | 说明 | 前端调用时机 |
|------|------|------|--------------|
| `/api/chat/session/create` | POST | 创建会话 | 点击"新建会话" |
| `/api/chat/conversations` | GET | 会话列表 | 页面加载、刷新 |
| `/api/chat/conversation/{cid}` | GET | 会话详情 | 切换会话 |
| `/api/chat/stream` | POST | 流式对话 | 发送消息 |
| `/api/chat/conversation/{cid}` | DELETE | 删除会话 | 删除操作 |

### SSE 流式处理

```typescript
// hooks/useChat.ts 核心逻辑

const sendMessage = async (cid: number, message: string) => {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cid, user_message: message }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    // 解析 SSE 格式: data: {"content": "..."}\n\n
    const lines = chunk.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (data.content) {
          // 更新 UI：追加内容
        }
        if (data.done) {
          // 流式结束
        }
      }
    }
  }
};
```

---

## 🚀 开发步骤

### Phase 1: 项目初始化

```bash
# 1. 创建 Vite 项目
npm create vite@latest . -- --template react-ts

# 2. 安装依赖
npm install

# 3. 安装 Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 4. 配置 Tailwind (tailwind.config.js)
# content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"]

# 5. 安装 shadcn/ui
npx shadcn@latest init

# 6. 安装需要的组件
npx shadcn@latest add button input scroll-area
```

### Phase 2: 核心组件开发

按以下顺序开发：

1. **types/index.ts** - 定义 Message、Conversation 类型
2. **lib/api.ts** - 封装 API 调用
3. **Layout.tsx** - 整体布局框架
4. **Sidebar.tsx** - 会话列表
5. **ChatArea.tsx** - 聊天区域
6. **MessageList.tsx** - 消息展示
7. **MessageItem.tsx** - 单条消息
8. **ChatInput.tsx** - 输入框
9. **hooks/useChat.ts** - SSE 处理

### Phase 3: API 对接

1. 配置 Vite 代理（解决跨域）
2. 实现 API 调用
3. 实现 SSE 流式处理
4. 状态管理（useState/useReducer）

### Phase 4: 样式优化

1. 响应式适配
2. 深色模式（可选）
3. 加载状态、错误处理
4. 动画效果

---

## ⚙️ 配置文件

### vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

---

## 🧪 本地开发

### 启动命令

```bash
# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
# 访问 http://localhost:3000

# 3. 构建生产版本
npm run build

# 4. 预览生产版本
npm run preview
```

### 环境要求

- Node.js 18+
- 后端服务运行在 http://localhost:8000

---

## 📝 开发日志

### 2025-12-24

- [ ] 创建项目结构
- [ ] 初始化 Vite + React + TypeScript
- [ ] 配置 Tailwind CSS
- [ ] 配置 shadcn/ui

---

## 🤝 协作规范

### 分支策略

- `feat/frontend` - 前端开发主分支
- 从 `feat/frontend` 创建功能分支

### 代码规范

- 使用 TypeScript 严格模式
- 组件使用函数式 + Hooks
- 样式使用 Tailwind CSS 类名
- 文件命名：PascalCase（组件）、camelCase（工具）

### Commit 规范

```bash
feat(frontend): add chat input component
fix(frontend): fix SSE connection issue
style(frontend): update message bubble style
```

---

**维护者：** @doraemon235  
**最后更新：** 2025-12-24

