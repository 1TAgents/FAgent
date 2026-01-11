"""
会话总结服务 - 自动生成会话标题

职责：
1. 接收对话消息列表
2. 调用 LLM 生成简短标题
3. 返回标题字符串
"""
import logging
from typing import List, Dict, Optional

from .llm import llm_service
from ..core.prompts import SUMMARY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class SummaryService:
    """会话总结服务"""
    
    def __init__(self):
        self.llm = llm_service
        logger.info("SummaryService 初始化完成")
    
    def generate_summary(
        self,
        messages: List[Dict],
        max_messages: int = 6
    ) -> str:
        """
        根据对话内容生成简短标题
        
        Args:
            messages: 对话消息列表 [{"role": "user/assistant", "content": "..."}]
            max_messages: 最多使用的消息数量（取最近的）
            
        Returns:
            str: 生成的标题（5-15字）
        """
        if not messages:
            return "新对话"
        
        # 只取最近的几条消息，避免 token 过多
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        # 构建用于总结的内容
        conversation_text = self._format_conversation(recent_messages)
        
        # 构建 LLM 请求
        llm_messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下对话生成一个简短标题：\n\n{conversation_text}"}
        ]
        
        logger.debug(f"生成会话总结 | messages_count={len(recent_messages)}")
        
        try:
            response = self.llm.chat_completion(
                messages=llm_messages,
                temperature=0.3,  # 低温度，输出更稳定
                max_tokens=50     # 标题不需要很长
            )
            
            title = response.choices[0].message.content.strip()
            
            # 清理标题（去除可能的引号、前缀等）
            title = self._clean_title(title)
            
            logger.info(f"会话总结生成成功 | title={title}")
            return title
            
        except Exception as e:
            logger.error(f"会话总结生成失败 | error={str(e)}")
            # 失败时返回第一条用户消息的前 15 个字
            return self._fallback_title(messages)
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """格式化对话内容"""
        lines = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            content = str(msg.get("content", ""))[:200]  # 截断过长内容
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
    
    def _clean_title(self, title: str) -> str:
        """清理生成的标题"""
        # 去除首尾引号和空白
        title = title.strip().strip('"\'「」『』【】《》')
        
        # 去除常见前缀（不区分大小写）
        prefixes = ["标题：", "标题:", "title:", "summary:", "主题：", "主题:"]
        lower_title = title.lower()
        for prefix in prefixes:
            if lower_title.startswith(prefix):
                title = title[len(prefix):].strip()
                break # 只要匹配到一个前缀就停止
        
        # 再次清理可能残留的引号
        title = title.strip('"\'')

        # 限制长度
        if len(title) > 15:
            title = title[:15]
        
        return title or "新对话"
    
    def _fallback_title(self, messages: List[Dict]) -> str:
        """生成失败时的备用标题"""
        for msg in messages:
            if msg.get("role") == "user":
                content = str(msg.get("content", ""))
                # 取前 15 个字
                title = content[:15]
                if len(content) > 15:
                    title += "..."
                return title
        return "新对话"


# 全局实例
summary_service = SummaryService()
