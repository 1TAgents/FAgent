"""
Cache - Redis 缓存层

提供行情、搜索等数据的缓存支持
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)


class DataCache:
    """
    数据缓存
    
    缓存策略：
    - 实时行情：60 秒 TTL
    - K 线数据：300 秒 TTL
    - 搜索结果：3600 秒 TTL
    - 股票列表：7200 秒 TTL
    """
    
    # TTL 配置（秒）
    TTL_QUOTE = 60          # 实时行情
    TTL_KLINE = 300         # K 线数据
    TTL_SEARCH = 3600       # 搜索结果
    TTL_STOCK_LIST = 7200   # 股票列表
    
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
        """获取缓存"""
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
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int = 300) -> bool:
        """设置缓存"""
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
    
    # ==================== 行情缓存 ====================
    
    def _make_quote_key(self, symbol: str, market: str = "A") -> str:
        """生成行情缓存键"""
        return f"quote:{market}:{symbol}"
    
    async def get_quote(self, symbol: str, market: str = "A") -> Optional[Dict]:
        """获取行情缓存"""
        key = self._make_quote_key(symbol, market)
        return await self.get(key)
    
    async def set_quote(self, symbol: str, data: Dict, ttl: int = None) -> bool:
        """
        设置行情缓存
        
        Args:
            symbol: 股票代码
            data: 行情数据
            ttl: 过期时间（秒），默认 60 秒
        """
        key = self._make_quote_key(symbol, data.get("market", "A"))
        return await self.set(key, data, ttl or self.TTL_QUOTE)
    
    # ==================== K 线缓存 ====================
    
    def _make_kline_key(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str
    ) -> str:
        """生成 K 线缓存键"""
        return f"kline:{symbol}:{period}:{start_date}:{end_date}"
    
    async def get_kline(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str
    ) -> Optional[Dict]:
        """获取 K 线缓存"""
        key = self._make_kline_key(symbol, period, start_date, end_date)
        return await self.get(key)
    
    async def set_kline(
        self,
        symbol: str,
        period: str,
        start_date: str,
        end_date: str,
        data: Dict
    ) -> bool:
        """设置 K 线缓存"""
        key = self._make_kline_key(symbol, period, start_date, end_date)
        return await self.set(key, data, self.TTL_KLINE)
    
    # ==================== 搜索缓存 ====================
    
    def _make_search_key(self, keyword: str, market: str, limit: int) -> str:
        """生成搜索缓存键"""
        safe_keyword = keyword.replace(":", "_").replace(" ", "_")
        return f"search:{market}:{safe_keyword}:{limit}"
    
    async def get_search(self, keyword: str, market: str = "A", limit: int = 10) -> Optional[Dict]:
        """获取搜索缓存"""
        key = self._make_search_key(keyword, market, limit)
        return await self.get(key)
    
    async def set_search(
        self,
        keyword: str,
        data: Dict,
        market: str = "A",
        limit: int = 10
    ) -> bool:
        """设置搜索缓存"""
        key = self._make_search_key(keyword, market, limit)
        return await self.set(key, data, self.TTL_SEARCH)
    
    # ==================== 股票列表缓存 ====================
    
    def _make_stock_list_key(self, market: str = "A") -> str:
        """生成股票列表缓存键"""
        return f"stocks:{market}"
    
    async def get_stock_list(self, market: str = "A") -> Optional[Dict]:
        """获取股票列表缓存"""
        key = self._make_stock_list_key(market)
        return await self.get(key)
    
    async def set_stock_list(self, data: Dict, market: str = "A") -> bool:
        """设置股票列表缓存"""
        key = self._make_stock_list_key(market)
        return await self.set(key, data, self.TTL_STOCK_LIST)
    
    # ==================== 批量操作 ====================
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        批量删除匹配模式的缓存
        
        Args:
            pattern: 匹配模式（如 "quote:A:*"）
            
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
    
    async def clear_all_quotes(self, market: str = "A") -> int:
        """清空所有行情缓存"""
        return await self.clear_pattern(f"quote:{market}:*")
    
    async def clear_all_klines(self, symbol: str = None) -> int:
        """
        清空 K 线缓存
        
        Args:
            symbol: 股票代码（None 表示清空所有）
        """
        if symbol:
            return await self.clear_pattern(f"kline:{symbol}:*")
        else:
            return await self.clear_pattern("kline:*")
    
    async def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis 连接已关闭")
