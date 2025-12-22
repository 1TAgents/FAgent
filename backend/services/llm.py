"""
LLM Service - 封装 OpenAI SDK 调用
"""
import os
from typing import Optional, Iterator
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from loguru import logger

# Load environment variables
load_dotenv(find_dotenv())


class LLMService:
    """LLM 服务类，封装 OpenAI SDK 调用"""
    
    def __init__(self):
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("openrounter_p")
        
        if not api_key:
            logger.error("OPENROUTER_API_KEY 环境变量未设置")
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model = os.getenv("LLM_MODEL", "xiaomi/mimo-v2-flash:free")
        logger.info(f"LLM 服务初始化完成 | model={self.model} | base_url={base_url}")
    
    def chat_completion(
        self,
        messages: list,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        非流式聊天完成
        
        Args:
            messages: 消息列表
            stream: 是否流式输出（False）
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数
            
        Returns:
            ChatCompletion 对象
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        # 支持 reasoning
        if "reasoning" in kwargs:
            params["extra_body"] = {"reasoning": kwargs["reasoning"]}
        
        logger.debug(f"LLM 非流式请求 | messages_count={len(messages)} | temp={temperature}")
        
        try:
            response = self.client.chat.completions.create(**params)
            
            # 记录 token 使用
            if response.usage:
                logger.info(
                    f"LLM 响应完成 | "
                    f"prompt_tokens={response.usage.prompt_tokens} | "
                    f"completion_tokens={response.usage.completion_tokens} | "
                    f"total_tokens={response.usage.total_tokens}"
                )
            
            return response
        except Exception as e:
            logger.error(f"LLM 调用失败 | error={str(e)}")
            raise
    
    def chat_completion_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        流式聊天完成
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数
            
        Yields:
            str: 流式返回的文本片段
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        # 支持 reasoning
        if "reasoning" in kwargs:
            params["extra_body"] = {"reasoning": kwargs["reasoning"]}
        
        logger.debug(f"LLM 流式请求 | messages_count={len(messages)} | temp={temperature}")
        
        try:
            stream = self.client.chat.completions.create(**params)
            chunk_count = 0
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    chunk_count += 1
                    yield chunk.choices[0].delta.content
            
            logger.debug(f"LLM 流式响应完成 | chunks={chunk_count}")
        except Exception as e:
            logger.error(f"LLM 流式调用失败 | error={str(e)}")
            raise


# 全局实例
llm_service = LLMService()
