"""
Data Service - 数据服务层

提供统一的股票数据访问接口，整合缓存、数据库、外部数据源
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import sqlite3
from pathlib import Path

from .database import StockDatabase
from .cache import DataCache
from .sync import DataSyncManager

logger = logging.getLogger(__name__)


class DataService:
    """
    数据服务
    
    统一管理股票数据的获取、缓存、存储
    """
    
    def __init__(
        self,
        db_path: str = "data/stock_data.db",
        redis_url: str = "redis://localhost:6379",
        cache_enabled: bool = True,
        auto_sync: bool = True
    ):
        """
        初始化数据服务
        
        Args:
            db_path: SQLite 数据库路径
            redis_url: Redis 连接 URL
            cache_enabled: 是否启用缓存
            auto_sync: 是否自动同步数据
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self.db = StockDatabase(str(self.db_path))
        logger.info(f"数据库初始化完成 | path={self.db_path}")
        
        # 初始化缓存
        self.cache = DataCache(redis_url, enabled=cache_enabled)
        if cache_enabled:
            logger.info(f"缓存已启用 | redis_url={redis_url}")
        else:
            logger.warning("缓存已禁用")
        
        # 初始化同步管理器
        self.sync_manager = DataSyncManager(self.db, self.cache)
        
        # 启动时自动同步
        if auto_sync:
            self._auto_sync_on_startup()
    
    def _auto_sync_on_startup(self):
        """启动时自动同步数据"""
        try:
            # 同步股票列表（如果为空或超过 7 天）
            if self.db.get_stock_count() == 0 or self.db.is_stock_list_old(days=7):
                logger.info("启动同步：更新股票列表...")
                self.sync_manager.sync_stock_list()
            
            # 同步最近 30 天的 K 线数据
            logger.info("启动同步：更新最近 30 天 K 线数据...")
            self.sync_manager.sync_recent_klines(days=30)
            
            logger.info("启动同步完成")
        except Exception as e:
            logger.error(f"启动同步失败 | error={e}")
    
    # ==================== 实时行情 ====================
    
    async def get_quote(self, symbol: str, market: str = "A") -> Optional[Dict[str, Any]]:
        """
        获取实时行情
        
        优先级：
        1. Redis 缓存（60 秒 TTL）
        2. AKShare 实时拉取
        3. 数据库（盘后数据）
        
        Args:
            symbol: 股票代码
            market: 市场类型
            
        Returns:
            行情数据字典
        """
        # 1. 尝试缓存
        cached = await self.cache.get_quote(symbol, market)
        if cached:
            logger.debug(f"缓存命中 | symbol={symbol}")
            return cached
        
        # 2. 尝试实时拉取
        try:
            import akshare as ak
            quote = await self._fetch_realtime_quote(ak, symbol, market)
            if quote:
                # 写入缓存
                await self.cache.set_quote(symbol, quote, ttl=60)
                logger.info(f"实时行情获取成功 | symbol={symbol}")
                return quote
        except Exception as e:
            logger.warning(f"实时行情获取失败 | symbol={symbol} | error={e}")
        
        # 3. 回退到数据库（最新一条）
        db_quote = self.db.get_latest_quote(symbol)
        if db_quote:
            logger.info(f"使用数据库行情 | symbol={symbol}")
            return db_quote
        
        logger.error(f"行情获取失败 | symbol={symbol}")
        return None
    
    async def _fetch_realtime_quote(self, ak, symbol: str, market: str) -> Optional[Dict]:
        """从 AKShare 获取实时行情"""
        if market == "A":
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == symbol]
            if not stock_data.empty:
                row = stock_data.iloc[0]
                return {
                    "symbol": symbol,
                    "name": row.get('名称', ''),
                    "market": market,
                    "price": float(row.get('最新价', 0)),
                    "open": float(row.get('今开', 0)),
                    "high": float(row.get('最高', 0)),
                    "low": float(row.get('最低', 0)),
                    "close": float(row.get('昨收', 0)),
                    "change": float(row.get('涨跌额', 0)),
                    "change_percent": float(row.get('涨跌幅', 0)),
                    "volume": int(float(row.get('成交量', 0)) * 100),
                    "turnover": float(row.get('成交额', 0)),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        return None
    
    # ==================== K 线数据 ====================
    
    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取 K 线数据
        
        优先级：
        1. 数据库（主）
        2. AKShare 补充（数据库缺失的日期）
        
        Args:
            symbol: 股票代码
            period: 周期 (daily/weekly/monthly)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            count: 返回条数
            
        Returns:
            K 线数据列表
        """
        # 1. 从数据库获取
        db_klines = self.db.get_kline(symbol, period, start_date, end_date, count)
        
        if db_klines and len(db_klines) >= count:
            logger.debug(f"数据库 K 线充足 | symbol={symbol} | count={len(db_klines)}")
            return db_klines
        
        # 2. 计算缺失的日期范围
        if db_klines:
            latest_date = db_klines[-1]['date']
            # 需要补充从 latest_date 到今天的数据
            logger.info(f"数据库 K 线不足，需要补充 | symbol={symbol} | from={latest_date}")
        else:
            latest_date = None
        
        # 3. 从 AKShare 补充
        try:
            import akshare as ak
            new_klines = await self._fetch_kline_from_ak(ak, symbol, period, latest_date)
            
            if new_klines:
                # 写入数据库
                self.db.save_kline(symbol, period, new_klines)
                logger.info(f"AKShare 补充 K 线 | symbol={symbol} | count={len(new_klines)}")
                
                # 合并数据
                if db_klines:
                    return db_klines + new_klines
                else:
                    return new_klines
        except Exception as e:
            logger.error(f"AKShare 补充 K 线失败 | symbol={symbol} | error={e}")
        
        # 4. 返回数据库数据（即使不完整）
        if db_klines:
            logger.warning(f"返回不完整 K 线 | symbol={symbol} | count={len(db_klines)}")
            return db_klines
        
        return []
    
    async def _fetch_kline_from_ak(
        self,
        ak,
        symbol: str,
        period: str,
        from_date: Optional[str] = None
    ) -> List[Dict]:
        """从 AKShare 获取 K 线"""
        try:
            # 计算日期范围
            if from_date:
                start = from_date
            else:
                start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            
            end = datetime.now().strftime("%Y%m%d")
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                adjust="qfq"
            )
            
            if df.empty:
                return []
            
            # 转换为字典列表
            klines = []
            for _, row in df.iterrows():
                kline = {
                    "date": str(row.get('日期', '')),
                    "open": float(row.get('开盘', 0)),
                    "high": float(row.get('最高', 0)),
                    "low": float(row.get('最低', 0)),
                    "close": float(row.get('收盘', 0)),
                    "volume": int(float(row.get('成交量', 0)) * 100),
                    "turnover": float(row.get('成交额', 0)) if '成交额' in row else None,
                    "change_percent": float(row.get('涨跌幅', 0)) if '涨跌幅' in row else None
                }
                klines.append(kline)
            
            return klines
            
        except Exception as e:
            logger.error(f"AKShare K 线获取失败 | symbol={symbol} | error={e}")
            return []
    
    # ==================== 股票列表 ====================
    
    async def get_stock_list(self, market: str = "A") -> List[Dict[str, Any]]:
        """
        获取股票列表
        
        优先级：
        1. 数据库
        2. AKShare 同步
        
        Args:
            market: 市场类型
            
        Returns:
            股票列表
        """
        # 1. 从数据库获取
        stocks = self.db.get_stock_list(market)
        
        if stocks and not self.db.is_stock_list_old(days=7):
            logger.debug(f"数据库股票列表充足 | count={len(stocks)}")
            return stocks
        
        # 2. 从 AKShare 同步
        try:
            logger.info("同步股票列表...")
            import akshare as ak
            df = ak.stock_info_a_code_name()
            
            stock_list = []
            for _, row in df.iterrows():
                stock = {
                    "symbol": str(row.get('code', '')),
                    "name": str(row.get('name', '')),
                    "market": market
                }
                stock_list.append(stock)
            
            # 保存到数据库
            self.db.save_stock_list(stock_list)
            logger.info(f"股票列表已同步 | count={len(stock_list)}")
            
            return stock_list
            
        except Exception as e:
            logger.error(f"股票列表同步失败 | error={e}")
            return stocks if stocks else []
    
    # ==================== 搜索 ====================
    
    async def search(self, keyword: str, market: str = "A", limit: int = 10) -> List[Dict]:
        """
        搜索股票
        
        Args:
            keyword: 关键词
            market: 市场类型
            limit: 返回数量
            
        Returns:
            搜索结果
        """
        # 从缓存获取
        cached = await self.cache.get_search(keyword, market, limit)
        if cached:
            return cached.get("items", [])
        
        # 从数据库搜索
        results = self.db.search_stock(keyword, market, limit)
        
        if results:
            # 写入缓存
            await self.cache.set_search(keyword, {"items": results}, market, limit, ttl=3600)
            return results
        
        return []
    
    # ==================== 数据同步 ====================
    
    async def sync_all(self, force: bool = False):
        """
        同步所有数据
        
        Args:
            force: 是否强制同步（忽略缓存和时间）
        """
        logger.info("开始全量同步...")
        
        # 1. 同步股票列表
        if force or self.db.is_stock_list_old(days=7):
            await self.sync_manager.sync_stock_list()
        
        # 2. 同步所有股票的最近 K 线
        await self.sync_manager.sync_recent_klines(days=30)
        
        logger.info("全量同步完成")
    
    async def sync_single_stock(self, symbol: str):
        """
        同步单只股票数据
        
        Args:
            symbol: 股票代码
        """
        logger.info(f"同步单只股票 | symbol={symbol}")
        await self.sync_manager.sync_stock_kline(symbol)
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "stock_count": self.db.get_stock_count(),
            "kline_records": self.db.get_kline_count(),
            "last_sync": self.db.get_last_sync_time(),
            "cache_enabled": self.cache.enabled
        }
    
    # ==================== 关闭连接 ====================
    
    async def close(self):
        """关闭所有连接"""
        self.db.close()
        await self.cache.close()
        logger.info("数据服务已关闭")


# 全局实例
_data_service: Optional[DataService] = None


def get_data_service(**kwargs) -> DataService:
    """获取全局数据服务实例"""
    global _data_service
    if _data_service is None:
        _data_service = DataService(**kwargs)
    return _data_service
