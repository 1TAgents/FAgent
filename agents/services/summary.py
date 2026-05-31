"""
会话总结服务 - 自动生成会话标题

职责：
1. 接收对话消息列表
2. 调用 LLM 生成简短标题
3. 返回标题字符串
"""
import logging
import re
from typing import List, Dict, Optional

from .llm import llm_service
from ..core.prompts import SUMMARY_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

ENGLISH_TITLE_MAP = {
    "capability qa smoke": "能力问答测试",
    "capability qa test": "能力问答测试",
    "self synthesis smoke": "自我介绍生成测试",
    "self info smoke": "自我介绍测试",
    "self info test": "自我介绍测试",
    "frontend proxy stream smoke": "前端流式代理测试",
    "stream smoke": "流式输出测试",
    "smoke test": "冒烟测试",
    "strategy": "策略研究",
    "general": "通用问答",
    "new chat": "新对话",
    "cli session": "命令行会话",
}


class SummaryService:
    """会话总结服务"""
    
    def __init__(self):
        self.llm = llm_service
        logger.info("SummaryService 初始化完成")
    
    async def generate_summary(
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
        localized_title = self._localize_from_messages(recent_messages)
        if localized_title:
            logger.info(f"会话总结规则生成成功 | title={localized_title}")
            return localized_title
        
        # 构建用于总结的内容
        conversation_text = self._format_conversation(recent_messages)
        
        # 构建 LLM 请求
        llm_messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下对话生成一个简短标题：\n\n{conversation_text}"}
        ]
        
        logger.debug(f"生成会话总结 | messages_count={len(recent_messages)}")
        
        try:
            response = await self.llm.chat_completion(
                messages=llm_messages,
                temperature=0.3,  # 低温度，输出更稳定
                max_tokens=50     # 标题不需要很长
            )
            
            title = response.choices[0].message.content.strip()
            
            # 清理标题（去除可能的引号、前缀等）
            title = self._clean_title(title)
            localized_title = self._localize_from_messages(recent_messages)
            if title == "新对话" and localized_title:
                title = localized_title
            
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
        title = self._localize_title(title)

        # 限制长度
        if len(title) > 15:
            title = title[:15]
        
        return title or "新对话"

    def _localize_from_messages(self, messages: List[Dict]) -> Optional[str]:
        """直接处理明显的英文内部测试标题，减少模型随机性。"""
        for msg in messages:
            if msg.get("role") != "user":
                continue
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            localized = self._localize_title(content)
            if localized != content:
                return localized[:15]
        return None

    def _localize_title(self, title: str) -> str:
        """将常见英文测试标题和内部意图词转为简体中文。"""
        normalized = re.sub(r"[\s_-]+", " ", title.strip().lower())
        normalized = normalized.strip(" .,:;!?，。；：！？")
        if not normalized:
            return title

        if normalized in ENGLISH_TITLE_MAP:
            return ENGLISH_TITLE_MAP[normalized]

        conversation_match = re.fullmatch(r"conversation\s+(\d+)", normalized)
        if conversation_match:
            return f"会话{conversation_match.group(1)}"

        words = set(normalized.split())
        if not _has_cjk(title) and {"capability", "qa"} <= words:
            return "能力问答测试" if "smoke" in words or "test" in words else "能力问答"
        if not _has_cjk(title) and "stream" in words:
            if "frontend" in words or "proxy" in words:
                return "前端流式代理测试"
            return "流式输出测试" if "smoke" in words or "test" in words else "流式输出"
        if not _has_cjk(title) and "self" in words and ({"info", "synthesis"} & words):
            return "自我介绍测试"
        return title
    
    def _fallback_title(self, messages: List[Dict]) -> str:
        """生成失败时的备用标题"""
        for msg in messages:
            if msg.get("role") == "user":
                content = str(msg.get("content", ""))
                # 取前 15 个字
                raw_title = content[:40]
                title = self._localize_title(raw_title)
                was_localized = title != raw_title
                if len(title) > 15:
                    title = title[:15]
                if len(content) > 15 and not was_localized:
                    title += "..."
                return title
        return "新对话"


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


# 全局实例
summary_service = SummaryService()
