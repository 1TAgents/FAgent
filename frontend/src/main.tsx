import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import 'highlight.js/styles/github-dark.css'
import App from './App'

// 默认启用深色模式
document.documentElement.classList.add('dark')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
