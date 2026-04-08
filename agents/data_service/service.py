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
        self._rq = None
        self._init_rqdata()
        
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

    def _init_rqdata(self):
        """初始化 RQData（可选）"""
        try:
            import rqdatac as rq
            rq.init()
            self._rq = rq
            logger.info("DataService 已启用 RQData 优先链路")
        except Exception as e:
            self._rq = None
            logger.warning(f"DataService 未启用 RQData，回退本地/AKShare | error={e}")

    def _get_raw_connection(self) -> sqlite3.Connection:
        """获取原始 SQLite 连接，用于读取聚宽脚本落库的数据"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _to_order_book_id(self, symbol: str) -> str:
        """转换为聚宽 order_book_id"""
        if "." in symbol:
            return symbol
        exchange = "XSHG" if symbol.startswith(("5", "6", "9")) else "XSHE"
        return f"{symbol}.{exchange}"

    def _lookup_local_name(self, symbol: str) -> str:
        """优先从本地聚宽表获取股票名称"""
        conn = self._get_raw_connection()
        try:
            cursor = conn.cursor()
            for sql in (
                "SELECT name FROM stock_info WHERE symbol = ? LIMIT 1",
                "SELECT name FROM stocks WHERE symbol = ? LIMIT 1",
            ):
                try:
                    row = cursor.execute(sql, (symbol,)).fetchone()
                    if row and row[0]:
                        return str(row[0])
                except sqlite3.OperationalError:
                    continue
        finally:
            conn.close()
        return ""

    def _get_local_quote_from_rq_tables(self, symbol: str, market: str) -> Optional[Dict[str, Any]]:
        """从本地聚宽历史表构造最新行情快照"""
        if market != "A":
            return None

        conn = self._get_raw_connection()
        try:
            cursor = conn.cursor()
            try:
                rows = cursor.execute(
                    """
                    SELECT datetime, open_price, high_price, low_price, close_price, volume, turnover
                    FROM bar_data
                    WHERE symbol = ? AND interval = '1d'
                    ORDER BY datetime DESC
                    LIMIT 2
                    """,
                    (symbol,),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []

            if not rows:
                return None

            latest = rows[0]
            prev_close = float(rows[1]["close_price"]) if len(rows) > 1 else float(latest["open_price"])
            latest_close = float(latest["close_price"])
            change = latest_close - prev_close
            change_percent = (change / prev_close * 100) if prev_close else 0.0
            turnover = float(latest["turnover"]) if latest["turnover"] is not None else 0.0

            return {
                "symbol": symbol,
                "name": self._lookup_local_name(symbol) or symbol,
                "market": market,
                "price": latest_close,
                "open": float(latest["open_price"]),
                "high": float(latest["high_price"]),
                "low": float(latest["low_price"]),
                "close": prev_close,
                "change": change,
                "change_percent": change_percent,
                "volume": int(float(latest["volume"])),
                "turnover": turnover,
                "timestamp": str(latest["datetime"]),
            }
        finally:
            conn.close()

    def _get_local_kline_from_rq_tables(self, symbol: str, period: str, count: int) -> List[Dict[str, Any]]:
        """从本地聚宽表读取 K 线"""
        conn = self._get_raw_connection()
        try:
            cursor = conn.cursor()
            rows = []

            if period == "daily":
                try:
                    rows = cursor.execute(
                        """
                        SELECT datetime, open_price, high_price, low_price, close_price, volume, turnover
                        FROM bar_data
                        WHERE symbol = ? AND interval = '1d'
                        ORDER BY datetime DESC
                        LIMIT ?
                        """,
                        (symbol, count),
                    ).fetchall()
                except sqlite3.OperationalError:
                    rows = []

                if rows:
                    return [
                        {
                            "date": str(row["datetime"])[:10],
                            "open": float(row["open_price"]),
                            "high": float(row["high_price"]),
                            "low": float(row["low_price"]),
                            "close": float(row["close_price"]),
                            "volume": int(float(row["volume"])),
                            "turnover": float(row["turnover"]) if row["turnover"] is not None else None,
                            "change_percent": None,
                        }
                        for row in reversed(rows)
                    ]
        finally:
            conn.close()

        return []

    def _search_local_rq_tables(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """从本地聚宽表搜索股票"""
        conn = self._get_raw_connection()
        try:
            cursor = conn.cursor()
            items: List[Dict[str, Any]] = []
            seen = set()
            like_keyword = f"%{keyword}%"

            queries = (
                """
                SELECT symbol, name, 'A' AS market, list_date, industry, area
                FROM stock_info
                WHERE symbol LIKE ? OR name LIKE ?
                ORDER BY symbol
                LIMIT ?
                """,
                """
                SELECT symbol, name, market, list_date, industry, area
                FROM stocks
                WHERE symbol LIKE ? OR name LIKE ?
                ORDER BY symbol
                LIMIT ?
                """,
            )

            for sql in queries:
                try:
                    rows = cursor.execute(sql, (like_keyword, like_keyword, limit)).fetchall()
                except sqlite3.OperationalError:
                    rows = []

                for row in rows:
                    symbol = str(row["symbol"])
                    if symbol in seen:
                        continue
                    seen.add(symbol)
                    items.append(
                        {
                            "symbol": symbol,
                            "name": str(row["name"]),
                            "market": str(row["market"]),
                            "list_date": str(row["list_date"]) if row["list_date"] else None,
                            "industry": str(row["industry"]) if row["industry"] else None,
                            "area": str(row["area"]) if row["area"] else None,
                        }
                    )
                    if len(items) >= limit:
                        return items
        finally:
            conn.close()

        return items

    def _get_stock_list_from_rq_tables(self) -> List[Dict[str, Any]]:
        """从本地聚宽表读取股票列表"""
        conn = self._get_raw_connection()
        try:
            cursor = conn.cursor()
            for sql in (
                "SELECT symbol, name, 'A' AS market, list_date, industry, area FROM stock_info ORDER BY symbol",
                "SELECT symbol, name, market, list_date, industry, area FROM stocks ORDER BY symbol",
            ):
                try:
                    rows = cursor.execute(sql).fetchall()
                except sqlite3.OperationalError:
                    rows = []

                if rows:
                    return [
                        {
                            "symbol": str(row["symbol"]),
                            "name": str(row["name"]),
                            "market": str(row["market"]),
                            "list_date": str(row["list_date"]) if row["list_date"] else None,
                            "industry": str(row["industry"]) if row["industry"] else None,
                            "area": str(row["area"]) if row["area"] else None,
                        }
                        for row in rows
                    ]
        finally:
            conn.close()

        return []

    async def _fetch_quote_from_rqdata(self, symbol: str, market: str) -> Optional[Dict]:
        """从 RQData 获取实时行情"""
        if market != "A" or self._rq is None:
            return None

        try:
            tick = self._rq.get_current_tick(self._to_order_book_id(symbol))
            if not tick:
                return None

            getter = tick.get if isinstance(tick, dict) else lambda key, default=None: getattr(tick, key, default)
            prev_close = getter("prev_close", getter("pre_close", 0)) or 0
            last_price = getter("last", getter("price", 0)) or 0
            turnover = float(getter("turnover", getter("total_turnover", 0)) or 0)
            change = last_price - prev_close if prev_close else 0.0

            return {
                "symbol": symbol,
                "name": self._lookup_local_name(symbol) or symbol,
                "market": market,
                "price": float(last_price or 0),
                "open": float(getter("open", prev_close or last_price) or 0),
                "high": float(getter("high", last_price) or 0),
                "low": float(getter("low", last_price) or 0),
                "close": float(prev_close or 0),
                "change": float(change),
                "change_percent": float(change / prev_close * 100) if prev_close else 0.0,
                "volume": int(float(getter("volume", 0) or 0)),
                "turnover": turnover,
                "timestamp": str(getter("datetime", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))),
            }
        except Exception as e:
            logger.warning(f"RQData 实时行情失败 | symbol={symbol} | error={e}")
            return None

    async def _fetch_kline_from_rqdata(self, symbol: str, period: str, count: int) -> List[Dict]:
        """从 RQData 获取日线"""
        if period != "daily" or self._rq is None:
            return []

        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=max(count * 3, 60))).strftime("%Y-%m-%d")
            df = self._rq.get_price(
                order_book_ids=self._to_order_book_id(symbol),
                start_date=start_date,
                end_date=end_date,
                frequency="1d",
                adjust_type="pre",
            )
            if df is None or df.empty:
                return []

            return [
                {
                    "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10],
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": int(float(row.get("volume", 0))),
                    "turnover": float(row.get("turnover", 0)) if row.get("turnover") is not None else None,
                    "change_percent": None,
                }
                for idx, row in df.tail(count).iterrows()
            ]
        except Exception as e:
            logger.warning(f"RQData K 线失败 | symbol={symbol} | error={e}")
            return []

    def _merge_klines_by_date(self, *groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按日期合并 K 线，后出现的数据覆盖前者"""
        merged: Dict[str, Dict[str, Any]] = {}
        for group in groups:
            for item in group:
                date_key = str(item.get("date", ""))
                if date_key:
                    merged[date_key] = item
        return [merged[key] for key in sorted(merged.keys())]
    
    # ==================== 实时行情 ====================
    
    async def get_quote(self, symbol: str, market: str = "A") -> Optional[Dict[str, Any]]:
        """
        获取实时行情
        
        优先级：
        1. Redis 缓存（60 秒 TTL）
        2. RQData 实时拉取
        3. 本地聚宽历史库快照
        4. AKShare 实时拉取
        5. 数据库（盘后数据）
        
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
        
        # 2. 优先尝试 RQData
        rq_quote = await self._fetch_quote_from_rqdata(symbol, market)
        if rq_quote:
            await self.cache.set_quote(symbol, rq_quote, ttl=60)
            logger.info(f"RQData 实时行情获取成功 | symbol={symbol}")
            return rq_quote

        # 3. 优先尝试本地聚宽历史库
        local_quote = self._get_local_quote_from_rq_tables(symbol, market)
        if local_quote:
            await self.cache.set_quote(symbol, local_quote, ttl=60)
            logger.info(f"本地聚宽库行情获取成功 | symbol={symbol}")
            return local_quote

        # 4. 尝试 AKShare 实时拉取
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
        
        # 5. 回退到数据库（最新一条）
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
        1. 本地聚宽历史库
        2. 业务数据库
        3. RQData 补充
        4. AKShare 补充（数据库缺失的日期）
        
        Args:
            symbol: 股票代码
            period: 周期 (daily/weekly/monthly)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            count: 返回条数
            
        Returns:
            K 线数据列表
        """
        # 1. 从本地聚宽历史库获取
        rq_local_klines = self._get_local_kline_from_rq_tables(symbol, period, count)
        if rq_local_klines and len(rq_local_klines) >= count:
            logger.debug(f"本地聚宽 K 线充足 | symbol={symbol} | count={len(rq_local_klines)}")
            return rq_local_klines

        # 2. 从业务数据库获取
        db_klines = self.db.get_kline(symbol, period, start_date, end_date, count)
        
        if db_klines and len(db_klines) >= count:
            logger.debug(f"数据库 K 线充足 | symbol={symbol} | count={len(db_klines)}")
            return db_klines
        
        # 3. 计算缺失的日期范围
        if db_klines:
            latest_date = db_klines[-1]['date']
            # 需要补充从 latest_date 到今天的数据
            logger.info(f"数据库 K 线不足，需要补充 | symbol={symbol} | from={latest_date}")
        else:
            latest_date = None
        
        # 4. 先用 RQData 补充
        rq_klines = await self._fetch_kline_from_rqdata(symbol, period, count)
        if rq_klines:
            logger.info(f"RQData 补充 K 线 | symbol={symbol} | count={len(rq_klines)}")
            if db_klines:
                return self._merge_klines_by_date(db_klines, rq_klines)
            if rq_local_klines:
                return self._merge_klines_by_date(rq_local_klines, rq_klines)
            return rq_klines

        # 5. 从 AKShare 补充
        try:
            import akshare as ak
            new_klines = await self._fetch_kline_from_ak(ak, symbol, period, latest_date)
            
            if new_klines:
                # 写入数据库
                self.db.save_kline(symbol, period, new_klines)
                logger.info(f"AKShare 补充 K 线 | symbol={symbol} | count={len(new_klines)}")
                
                # 合并数据
                if db_klines:
                    return self._merge_klines_by_date(db_klines, new_klines)
                else:
                    return new_klines
        except Exception as e:
            logger.error(f"AKShare 补充 K 线失败 | symbol={symbol} | error={e}")
        
        # 6. 返回已有数据（即使不完整）
        if rq_local_klines:
            logger.warning(f"返回本地聚宽不完整 K 线 | symbol={symbol} | count={len(rq_local_klines)}")
            return rq_local_klines
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
        # 1. 优先从本地聚宽表获取
        stocks = self._get_stock_list_from_rq_tables() if market == "A" else []
        if stocks:
            logger.debug(f"本地聚宽股票列表充足 | count={len(stocks)}")
            return stocks

        # 2. 从数据库获取
        stocks = self.db.get_stock_list(market)
        
        if stocks and not self.db.is_stock_list_old(days=7):
            logger.debug(f"数据库股票列表充足 | count={len(stocks)}")
            return stocks
        
        # 3. 从 RQData 获取
        if market == "A" and self._rq is not None:
            try:
                instruments = self._rq.all_instruments(type="CS", market="cn")
                stock_list = []
                for _, row in instruments.iterrows():
                    stock_list.append(
                        {
                            "symbol": str(row.get("order_book_id", "")).split(".")[0],
                            "name": str(row.get("symbol_name", "")),
                            "market": market,
                        }
                    )

                if stock_list:
                    logger.info(f"RQData 股票列表获取成功 | count={len(stock_list)}")
                    self.db.save_stock_list(stock_list)
                    return stock_list
            except Exception as e:
                logger.warning(f"RQData 股票列表获取失败 | error={e}")

        # 4. 从 AKShare 同步
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
        
        # 优先从本地聚宽表搜索
        if market == "A":
            local_results = self._search_local_rq_tables(keyword, limit)
            if local_results:
                await self.cache.set_search(keyword, {"items": local_results}, market, limit, ttl=3600)
                return local_results

        # 从数据库搜索
        results = self.db.search_stock(keyword, market, limit)
        
        if results:
            await self.cache.set_search(keyword, {"items": results}, market, limit, ttl=3600)
            return results

        if market == "A" and self._rq is not None:
            try:
                instruments = self._rq.all_instruments(type="CS", market="cn")
                mask = (
                    instruments["order_book_id"].astype(str).str.contains(keyword, na=False, case=False)
                    | instruments["symbol_name"].astype(str).str.contains(keyword, na=False, case=False)
                )
                matches = instruments[mask].head(limit)
                rq_results = [
                    {
                        "symbol": str(row.get("order_book_id", "")).split(".")[0],
                        "name": str(row.get("symbol_name", "")),
                        "market": market,
                    }
                    for _, row in matches.iterrows()
                ]
                if rq_results:
                    await self.cache.set_search(keyword, {"items": rq_results}, market, limit, ttl=3600)
                    return rq_results
            except Exception as e:
                logger.warning(f"RQData 搜索失败 | keyword={keyword} | error={e}")
        
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
    
    async def sync_stock_list(self) -> Dict[str, Any]:
        """
        同步股票列表
        
        Returns:
            同步结果
        """
        try:
            count = await self.sync_manager.sync_stock_list()
            return {
                "success": True,
                "count": count,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def sync_klines(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500
    ) -> Dict[str, Any]:
        """
        同步单只股票 K 线数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）
            limit: 同步条数限制
            
        Returns:
            同步结果
        """
        try:
            count = await self.sync_manager.sync_kline_range(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            return {
                "success": True,
                "symbol": symbol,
                "count": count
            }
        except Exception as e:
            logger.error(f"同步 K 线失败 | symbol={symbol} | error={e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取数据统计信息（异步版本）
        
        Returns:
            统计信息字典
        """
        return self.get_stats()
    
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
