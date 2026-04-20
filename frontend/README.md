# Frontend 模块

当前前端是一个基于 React 19 + Vite 7 的 Web 应用，负责聊天界面、会话侧边栏、认证弹窗和模型选择等交互。

## 技术栈

- React 19
- TypeScript 5
- Vite 7
- Tailwind CSS 3
- Radix UI
- Lucide React

## 当前功能

- ChatGPT 风格的双栏聊天界面
- 会话分组侧边栏（Today / Yesterday / Previous 7 Days 等）
- 新建会话、切换会话、重命名、删除
- SSE 流式消息渲染
- 登录 / 注册弹窗与本地 Token 持久化
- 动态获取模型列表
- 默认深色主题

## 目录

```text
frontend/src/
├── components/
├── context/
├── hooks/
├── lib/
├── api/
└── types/
```

## 启动

```bash
cd frontend
npm install
npm run dev
```

默认开发地址：

- `http://localhost:5173`

## 与后端联调

`vite.config.ts` 已配置开发代理：

- `/api` -> `http://localhost:8000`

所以本地开发时通常只需要确保 Backend 跑在 `8000`，无需在浏览器里直接请求 Agents。

## 当前实现说明

- 会话数据来自 `frontend/src/lib/api.ts`
- 鉴权状态通过 `AuthContext` 保存在 `localStorage`
- 当 Backend 不可用时，部分交互会退回到开发态 mock 行为，便于继续看 UI
- `MarketSwitcher` / `MarketChatExample` 目前更偏实验组件，不是当前主页面入口

## 生产前需要注意

- 当前前端默认依赖 Vite 开发代理；生产部署需要显式配置反向代理
- 登录弹窗里的 mock fallback 只适合本地开发，正式环境应关闭或替换
- 如果你调整了 Backend 端口，需要同步更新 `vite.config.ts` 代理目标
