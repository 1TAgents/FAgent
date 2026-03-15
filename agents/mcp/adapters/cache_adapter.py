"""
Cache Adapter - Redis 缓存适配器

为 MCP 工具调用提供缓存支持，减少重复请求
"""
import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheAdapter:
    """
    Redis 缓存适配器
    
    用法:
        cache = CacheAdapter(redis_url="redis://localhost:6379")
        await cache.set("key", {"data": "value"}, ttl=300)
        data = await cache.get("key")
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", enabled: bool = True):
        """
        初始化缓存
        
        Args:
            redis_url: Redis 连接 URL
            enabled: 是否启用缓存
        """
        self.redis_url = redis_url
        self.enabled = enabled
        self._redis = None
        
        if enabled:
            self._init_redis()
    
    def _init_redis(self):
        """延迟加载 Redis"""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Redis 连接成功 | url={self.redis_url}")
        except ImportError:
            logger.warning("Redis 未安装，缓存功能将禁用。请执行：pip install redis")
            self.enabled = False
        except Exception as e:
            logger.warning(f"Redis 连接失败 | error={e}，缓存功能将禁用")
            self.enabled = False
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据，不存在返回 None
        """
        if not self.enabled or not self._redis:
            return None
        
        try:
            value = await self._redis.get(key)
            if value:
                logger.debug(f"缓存命中 | key={key}")
                return json.loads(value)
            logger.debug(f"缓存未命中 | key={key}")
            return None
        except Exception as e:
            logger.warning(f"获取缓存失败 | key={key} | error={e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: int = 300
    ) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值（字典）
            ttl: 过期时间（秒），默认 5 分钟
            
        Returns:
            是否成功
        """
        if not self.enabled or not self._redis:
            return False
        
        try:
            await self._redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            logger.debug(f"缓存已设置 | key={key} | ttl={ttl}s")
            return True
        except Exception as e:
            logger.warning(f"设置缓存失败 | key={key} | error={e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled or not self._redis:
            return False
        
        try:
            await self._redis.delete(key)
            logger.debug(f"缓存已删除 | key={key}")
            return True
        except Exception as e:
            logger.warning(f"删除缓存失败 | key={key} | error={e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        批量删除匹配模式的缓存
        
        Args:
            pattern: 匹配模式（如 "stock_quote:*"）
            
        Returns:
            删除的数量
        """
        if not self.enabled or not self._redis:
            return 0
        
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                count = await self._redis.delete(*keys)
                logger.info(f"批量删除缓存 | pattern={pattern} | count={count}")
                return count
            return 0
        except Exception as e:
            logger.warning(f"批量删除缓存失败 | pattern={pattern} | error={e}")
            return 0
    
    # ==================== 行情相关缓存方法 ====================
    
    def _make_quote_key(self, symbol: str, market: str = "A") -> str:
        """生成行情缓存键"""
        return f"stock_quote:{market}:{symbol}"
    
    async def get_quote(self, symbol: str, market: str = "A") -> Optional[Dict]:
        """获取行情缓存"""
        key = self._make_quote_key(symbol, market)
        return await self.get(key)
    
    async def set_quote(
        self,
        symbol: str,
        data: Dict,
        ttl: int = 60
    ) -> bool:
        """
        设置行情缓存
        
        Args:
            symbol: 股票代码
            data: 行情数据
            ttl: 过期时间（秒），行情默认 1 分钟
        """
        key = self._make_quote_key(symbol, market=data.get("market", "A"))
        return await self.set(key, data, ttl)
    
    # ==================== K 线相关缓存方法 ====================
    
    def _make_kline_key(
        self,
        symbol: str,
        period: str,
        count: int,
        market: str = "A"
    ) -> str:
        """生成 K 线缓存键"""
        return f"stock_kline:{market}:{symbol}:{period}:{count}"
    
    async def get_kline(
        self,
        symbol: str,
        period: str,
        count: int,
        market: str = "A"
    ) -> Optional[Dict]:
        """获取 K 线缓存"""
        key = self._make_kline_key(symbol, period, count, market)
        return await self.get(key)
    
    async def set_kline(
        self,
        symbol: str,
        period: str,
        count: int,
        data: Dict,
        ttl: int = 300
    ) -> bool:
        """
        设置 K 线缓存
        
        Args:
            symbol: 股票代码
            period: 周期
            count: 条数
            data: K 线数据
            ttl: 过期时间（秒），K 线默认 5 分钟
        """
        key = self._make_kline_key(symbol, period, count, data.get("market", "A"))
        return await self.set(key, data, ttl)
    
    # ==================== 搜索相关缓存方法 ====================
    
    def _make_search_key(self, keyword: str, market: str = "A", limit: int = 10) -> str:
        """生成搜索缓存键"""
        # 处理关键词中的特殊字符
        safe_keyword = keyword.replace(":", "_").replace(" ", "_")
        return f"stock_search:{market}:{safe_keyword}:{limit}"
    
    async def get_search(
        self,
        keyword: str,
        market: str = "A",
        limit: int = 10
    ) -> Optional[Dict]:
        """获取搜索缓存"""
        key = self._make_search_key(keyword, market, limit)
        return await self.get(key)
    
    async def set_search(
        self,
        keyword: str,
        data: Dict,
        market: str = "A",
        limit: int = 10,
        ttl: int = 3600
    ) -> bool:
        """
        设置搜索缓存
        
        Args:
            keyword: 关键词
            data: 搜索结果
            market: 市场类型
            limit: 返回数量
            ttl: 过期时间（秒），搜索默认 1 小时
        """
        key = self._make_search_key(keyword, market, limit)
        return await self.set(key, data, ttl)
    
    async def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis 连接已关闭")


# 全局缓存实例
_mcp_cache: Optional[CacheAdapter] = None


def get_mcp_cache(redis_url: str = "redis://localhost:6379") -> CacheAdapter:
    """获取全局缓存实例"""
    global _mcp_cache
    if _mcp_cache is None:
        _mcp_cache = CacheAdapter(redis_url)
    return _mcp_cache
