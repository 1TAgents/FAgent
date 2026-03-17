"""
Data Sync - 数据同步管理器

负责定时同步、增量更新、数据校验
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncio

from .database import StockDatabase
from .cache import DataCache

logger = logging.getLogger(__name__)


class DataSyncManager:
    """
    数据同步管理器
    
    同步策略：
    1. 股票列表 - 每周更新
    2. K 线数据 - 每日盘后更新
    3. 实时行情 - 按需拉取（不存储）
    """
    
    def __init__(self, db: StockDatabase, cache: DataCache):
        """
        初始化同步管理器
        
        Args:
            db: 数据库实例
            cache: 缓存实例
        """
        self.db = db
        self.cache = cache
        self._ak = None
    
    def _get_ak(self):
        """延迟加载 AKShare"""
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak
    
    # ==================== 股票列表同步 ====================
    
    async def sync_stock_list(self) -> int:
        """
        同步股票列表
        
        Returns:
            同步的股票数量
        """
        try:
            ak = self._get_ak()
            logger.info("开始同步股票列表...")
            
            # 从 AKShare 获取
            df = ak.stock_info_a_code_name()
            
            stock_list = []
            for _, row in df.iterrows():
                stock = {
                    "symbol": str(row.get('code', '')),
                    "name": str(row.get('name', '')),
                    "market": "A"
                }
                stock_list.append(stock)
            
            # 保存到数据库
            self.db.save_stock_list(stock_list)
            
            # 更新缓存
            await self.cache.set_stock_list({"items": stock_list})
            
            # 记录日志
            self.db.log_sync("stock_list", records=len(stock_list), status="success")
            
            logger.info(f"股票列表同步完成 | count={len(stock_list)}")
            return len(stock_list)
            
        except Exception as e:
            logger.error(f"股票列表同步失败 | error={e}")
            self.db.log_sync("stock_list", status="failed", error=str(e))
            raise
    
    # ==================== K 线数据同步 ====================
    
    async def sync_recent_klines(self, days: int = 30, max_workers: int = 5):
        """
        同步最近 N 天的 K 线数据
        
        Args:
            days: 同步天数
            max_workers: 并发数
        """
        try:
            logger.info(f"开始同步最近{days}天 K 线数据...")
            
            # 获取所有股票
            stocks = self.db.get_stock_list()
            
            if not stocks:
                logger.warning("股票列表为空，先同步股票列表")
                await self.sync_stock_list()
                stocks = self.db.get_stock_list()
            
            logger.info(f"待同步股票数：{len(stocks)}")
            
            # 分批同步（避免并发过高）
            batch_size = max_workers
            total_count = 0
            
            for i in range(0, len(stocks), batch_size):
                batch = stocks[i:i + batch_size]
                tasks = [self.sync_stock_kline(stock['symbol'], days) for stock in batch]
                
                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, int):
                            total_count += result
                        elif isinstance(result, Exception):
                            logger.warning(f"单只股票同步失败 | error={result}")
                except Exception as e:
                    logger.error(f"批次同步失败 | batch={i//batch_size} | error={e}")
                
                # 每批之间暂停，避免请求过快
                if i + batch_size < len(stocks):
                    await asyncio.sleep(0.5)
                
                logger.info(f"进度：{i + batch_size}/{len(stocks)}")
            
            logger.info(f"K 线同步完成 | total_records={total_count}")
            self.db.log_sync("kline_recent", records=total_count, status="success")
            
        except Exception as e:
            logger.error(f"K 线同步失败 | error={e}")
            self.db.log_sync("kline_recent", status="failed", error=str(e))
            raise
    
    async def sync_stock_kline(self, symbol: str, days: int = 30) -> int:
        """
        同步单只股票的 K 线数据
        
        Args:
            symbol: 股票代码
            days: 同步天数
            
        Returns:
            同步的记录数
        """
        return await self.sync_kline_range(symbol, days=days, limit=500)
    
    async def sync_kline_range(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500
    ) -> int:
        """
        同步指定范围的 K 线数据
        
        Args:
            symbol: 股票代码
            days: 同步天数（当 start_date/end_date 未指定时使用）
            start_date: 开始日期（YYYYMMDD 或 YYYY-MM-DD）
            end_date: 结束日期（YYYYMMDD 或 YYYY-MM-DD）
            limit: 同步条数限制
            
        Returns:
            同步的记录数
        """
        try:
            ak = self._get_ak()
            logger.debug(f"开始同步 K 线 | symbol={symbol}, start={start_date}, end={end_date}")
            
            # 计算日期范围
            if not end_date:
                end_dt = datetime.now()
            else:
                end_dt = datetime.strptime(str(end_date).replace("-", ""), "%Y%m%d")
            
            if not start_date:
                start_dt = end_dt - timedelta(days=days)
            else:
                start_dt = datetime.strptime(str(start_date).replace("-", ""), "%Y%m%d")
            
            # 从 AKShare 获取
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_dt.strftime("%Y%m%d"),
                end_date=end_dt.strftime("%Y%m%d"),
                adjust="qfq"
            )
            
            if df.empty:
                logger.warning(f"无 K 线数据 | symbol={symbol}")
                return 0
            
            # 限制条数
            if len(df) > limit:
                df = df.tail(limit)
            
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
            
            # 保存到数据库
            self.db.save_kline(symbol, "daily", klines)
            
            logger.debug(f"K 线已同步 | symbol={symbol} | count={len(klines)}")
            return len(klines)
            
        except Exception as e:
            logger.warning(f"单只股票 K 线同步失败 | symbol={symbol} | error={e}")
            self.db.log_sync("kline_single", symbol=symbol, status="failed", error=str(e))
            return 0
    
    # ==================== 定时任务 ====================
    
    async def start_scheduler(self):
        """
        启动定时同步任务
        
        调度计划：
        - 每个交易日 15:30 - 同步当日 K 线
        - 每周六 02:00 - 同步股票列表
        """
        logger.info("定时同步任务已启动")
        
        # 这里可以集成 APScheduler 或其他调度库
        # 简单实现：定期检查并同步
        
        while True:
            try:
                now = datetime.now()
                
                # 交易日 15:30 同步
                if now.hour == 15 and now.minute == 30 and now.weekday() < 5:
                    logger.info("定时任务：同步当日 K 线")
                    await self.sync_recent_klines(days=1)
                
                # 周六 02:00 同步股票列表
                if now.hour == 2 and now.minute == 0 and now.weekday() == 5:
                    logger.info("定时任务：同步股票列表")
                    await self.sync_stock_list()
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("定时同步任务已停止")
                break
            except Exception as e:
                logger.error(f"定时任务执行失败 | error={e}")
                await asyncio.sleep(60)
    
    # ==================== 数据校验 ====================
    
    def validate_data(self, symbol: str) -> Dict:
        """
        校验数据完整性
        
        Args:
            symbol: 股票代码
            
        Returns:
            校验结果
        """
        result = {
            "symbol": symbol,
            "valid": True,
            "issues": []
        }
        
        # 检查 K 线连续性
        klines = self.db.get_kline(symbol, "daily", count=100)
        
        if not klines:
            result["valid"] = False
            result["issues"].append("无 K 线数据")
            return result
        
        # 检查是否有缺失日期（简化版，只检查最近 10 条）
        recent = klines[-10:]
        for i in range(1, len(recent)):
            prev_date = datetime.strptime(recent[i-1]['date'], "%Y-%m-%d")
            curr_date = datetime.strptime(recent[i]['date'], "%Y-%m-%d")
            diff = (curr_date - prev_date).days
            
            # 跳过周末
            if diff > 3 and prev_date.weekday() < 4:
                result["valid"] = False
                result["issues"].append(f"日期不连续：{recent[i-1]['date']} 到 {recent[i]['date']}")
        
        return result
