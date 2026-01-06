"""
Market Client - 行情数据源客户端

封装 AKShare 调用，提供统一的数据获取接口

优化：
- 添加内存缓存，减少重复请求
- 单股票查询使用更快的 API
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from .models import (
    StockQuote, 
    KLineData, 
    StockInfo, 
    Market, 
    KLinePeriod
)
from .cache import market_cache

logger = logging.getLogger(__name__)


class AKShareClient:
    """
    AKShare 数据源客户端
    
    文档: https://akshare.akfamily.xyz/
    
    优化策略：
    1. 单股票查询：使用 stock_individual_info_em（快）
    2. 批量查询时：使用 stock_zh_a_spot_em + 缓存
    """
    
    def __init__(self):
        self._ak = None
        self._last_trade_date: Optional[date] = None
        self._init_akshare()
    
    def _init_akshare(self):
        """延迟加载 akshare"""
        try:
            import akshare as ak
            self._ak = ak
            logger.info("AKShare 初始化成功")
        except ImportError:
            logger.error("AKShare 未安装，请执行: pip install akshare")
            raise ImportError("请安装 akshare: pip install akshare")
    
    @property
    def ak(self):
        """获取 akshare 模块"""
        if self._ak is None:
            self._init_akshare()
        return self._ak
    
    # ==================== 交易日期 ====================
    
    def get_last_trade_date(self) -> Optional[date]:
        """
        获取最近的交易日期
        
        通过判断当前时间和市场开盘时间来推断
        """
        # 使用缓存
        if self._last_trade_date:
            return self._last_trade_date
        
        try:
            # 获取最近一个交易日的 K 线来确定日期
            # 使用一个流通性好的股票
            df = self.ak.stock_zh_a_hist(
                symbol="000001",  # 平安银行
                period="daily",
                start_date=(datetime.now() - timedelta(days=10)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust=""
            )
            
            if not df.empty:
                last_date_str = str(df.iloc[-1]["日期"])
                self._last_trade_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                logger.info(f"最近交易日: {self._last_trade_date}")
                return self._last_trade_date
        except Exception as e:
            logger.warning(f"获取最近交易日失败 | error={e}")
        
        # 回退：使用简单推断
        today = date.today()
        # 如果是周末，回退到周五
        if today.weekday() == 5:  # 周六
            self._last_trade_date = today - timedelta(days=1)
        elif today.weekday() == 6:  # 周日
            self._last_trade_date = today - timedelta(days=2)
        else:
            # 工作日，如果当前时间在 15:00 之前，可能是昨天的数据
            now = datetime.now()
            if now.hour < 15:
                # 可能还没收盘，用昨天（需要考虑周一的情况）
                if today.weekday() == 0:  # 周一
                    self._last_trade_date = today - timedelta(days=3)  # 上周五
                else:
                    self._last_trade_date = today - timedelta(days=1)
            else:
                self._last_trade_date = today
        
        return self._last_trade_date
    
    # ==================== A股 ====================
    
    def get_a_share_quote(self, symbol: str, use_cache: bool = True) -> Optional[StockQuote]:
        """
        获取 A 股实时行情（优化版，使用缓存）
        
        策略：使用全市场 API + 缓存
        - 第一次请求：下载全市场数据（约 30-60s），缓存 30 秒
        - 后续请求：直接从缓存获取（0s）
        
        Args:
            symbol: 股票代码，如 "600519"、"000001"
            use_cache: 是否使用缓存
            
        Returns:
            StockQuote 或 None
        """
        # 1. 检查单股票缓存
        cache_key = f"quote:{symbol}"
        if use_cache:
            cached = market_cache.get(cache_key)
            if cached:
                return cached
        
        # 2. 从全市场数据获取（有缓存）
        quote = self._get_quote_from_all(symbol, use_cache)
        if quote:
            market_cache.set(cache_key, quote, cache_type="quote")
        return quote
    
    def _get_quote_from_all(self, symbol: str, use_cache: bool = True) -> Optional[StockQuote]:
        """
        从全市场数据中获取行情（有缓存）
        """
        try:
            # 检查全市场缓存
            cache_key = "quote_all:a_share"
            df = None
            
            if use_cache:
                df = market_cache.get(cache_key)
            
            if df is None:
                logger.info("获取全市场 A 股数据...")
                df = self.ak.stock_zh_a_spot_em()
                market_cache.set(cache_key, df, cache_type="quote_all")
                logger.info(f"全市场数据已缓存 | count={len(df)}")
            
            # 查找股票
            row = df[df["代码"] == symbol]
            if row.empty:
                logger.warning(f"未找到股票: {symbol}")
                return None
            
            row = row.iloc[0]
            
            return StockQuote(
                symbol=symbol,
                name=row["名称"],
                price=self._parse_float(row.get("最新价", 0)),
                change=self._parse_float(row.get("涨跌额", 0)),
                change_pct=self._parse_float(row.get("涨跌幅", 0)),
                open=self._parse_float(row.get("今开", 0)),
                high=self._parse_float(row.get("最高", 0)),
                low=self._parse_float(row.get("最低", 0)),
                prev_close=self._parse_float(row.get("昨收", 0)),
                volume=int(self._parse_float(row.get("成交量", 0))),
                amount=self._parse_float(row.get("成交额", 0)),
                timestamp=datetime.now(),
                market=Market.A_SHARE,
                trade_date=self.get_last_trade_date(),
            )
        except Exception as e:
            logger.error(f"获取 A 股行情失败 | symbol={symbol} | error={e}")
            return None
    
    def _parse_float(self, value) -> float:
        """安全解析浮点数"""
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def get_a_share_kline(
        self, 
        symbol: str, 
        period: KLinePeriod = KLinePeriod.DAILY,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: int = 100,
        use_cache: bool = True
    ) -> Optional[KLineData]:
        """
        获取 A 股 K 线数据
        
        Args:
            symbol: 股票代码
            period: K线周期
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            count: 返回条数（当不指定日期时）
            use_cache: 是否使用缓存
            
        Returns:
            KLineData 或 None
        """
        # 检查缓存
        cache_key = f"kline:{symbol}:{period.value}:{count}"
        if use_cache:
            cached = market_cache.get(cache_key)
            if cached:
                return cached
        
        try:
            # 日K线
            if period == KLinePeriod.DAILY:
                df = self.ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date or "20200101",
                    end_date=end_date or datetime.now().strftime("%Y%m%d"),
                    adjust="qfq"  # 前复权
                )
            # 分钟K线
            elif period in [KLinePeriod.MIN_1, KLinePeriod.MIN_5, 
                           KLinePeriod.MIN_15, KLinePeriod.MIN_30, KLinePeriod.MIN_60]:
                period_map = {
                    KLinePeriod.MIN_1: "1",
                    KLinePeriod.MIN_5: "5",
                    KLinePeriod.MIN_15: "15",
                    KLinePeriod.MIN_30: "30",
                    KLinePeriod.MIN_60: "60",
                }
                df = self.ak.stock_zh_a_hist_min_em(
                    symbol=symbol,
                    period=period_map[period],
                    adjust="qfq"
                )
            else:
                logger.warning(f"暂不支持的 K 线周期: {period}")
                return None
            
            if df.empty:
                return None
            
            # 只取最近 count 条
            df = df.tail(count)
            
            # 转换为标准格式
            data = []
            for _, row in df.iterrows():
                data.append({
                    "date": str(row.get("日期", row.get("时间", ""))),
                    "open": float(row["开盘"]),
                    "high": float(row["最高"]),
                    "low": float(row["最低"]),
                    "close": float(row["收盘"]),
                    "volume": int(row["成交量"]),
                    "amount": float(row.get("成交额", 0)),
                })
            
            result = KLineData(
                symbol=symbol,
                period=period,
                data=data,
            )
            
            # 缓存结果
            market_cache.set(cache_key, result, cache_type="kline")
            
            return result
        except Exception as e:
            logger.error(f"获取 A 股 K 线失败 | symbol={symbol} | error={e}")
            return None
    
    def search_a_share(self, keyword: str, limit: int = 10, use_cache: bool = True) -> List[StockInfo]:
        """
        搜索 A 股股票
        
        Args:
            keyword: 关键词（代码或名称）
            limit: 返回条数
            use_cache: 是否使用缓存
            
        Returns:
            StockInfo 列表
        """
        # 检查缓存
        cache_key = f"search:{keyword}:{limit}"
        if use_cache:
            cached = market_cache.get(cache_key)
            if cached:
                return cached
        
        try:
            # 使用全市场数据（有缓存）
            cache_key_all = "quote_all:a_share"
            df = market_cache.get(cache_key_all)
            
            if df is None:
                df = self.ak.stock_zh_a_spot_em()
                market_cache.set(cache_key_all, df, cache_type="quote_all")
            
            # 按代码或名称搜索
            mask = (
                df["代码"].str.contains(keyword, case=False, na=False) |
                df["名称"].str.contains(keyword, case=False, na=False)
            )
            results_df = df[mask].head(limit)
            
            results = [
                StockInfo(
                    symbol=row["代码"],
                    name=row["名称"],
                    market=Market.A_SHARE,
                )
                for _, row in results_df.iterrows()
            ]
            
            # 缓存搜索结果
            market_cache.set(cache_key, results, cache_type="search")
            
            return results
        except Exception as e:
            logger.error(f"搜索 A 股失败 | keyword={keyword} | error={e}")
            return []
    
    # ==================== 美股 ====================
    
    def get_us_stock_quote(self, symbol: str, use_cache: bool = True) -> Optional[StockQuote]:
        """
        获取美股实时行情
        
        Args:
            symbol: 股票代码，如 "AAPL"、"TSLA"
            use_cache: 是否使用缓存
            
        Returns:
            StockQuote 或 None
        """
        # 检查缓存
        cache_key = f"quote:us:{symbol.upper()}"
        if use_cache:
            cached = market_cache.get(cache_key)
            if cached:
                return cached
        
        try:
            # 检查全市场缓存
            cache_key_all = "quote_all:us"
            df = market_cache.get(cache_key_all) if use_cache else None
            
            if df is None:
                df = self.ak.stock_us_spot_em()
                market_cache.set(cache_key_all, df, cache_type="quote_all")
            
            row = df[df["代码"].str.upper() == symbol.upper()]
            if row.empty:
                # 尝试按名称匹配
                row = df[df["名称"].str.contains(symbol, case=False, na=False)]
            
            if row.empty:
                logger.warning(f"未找到美股: {symbol}")
                return None
            
            row = row.iloc[0]
            
            quote = StockQuote(
                symbol=row["代码"],
                name=row["名称"],
                price=self._parse_float(row.get("最新价", 0)),
                change=self._parse_float(row.get("涨跌额", 0)),
                change_pct=self._parse_float(row.get("涨跌幅", 0)),
                open=self._parse_float(row.get("今开", 0)),
                high=self._parse_float(row.get("最高", 0)),
                low=self._parse_float(row.get("最低", 0)),
                prev_close=self._parse_float(row.get("昨收", 0)),
                volume=int(self._parse_float(row.get("成交量", 0))),
                amount=self._parse_float(row.get("成交额", 0)),
                timestamp=datetime.now(),
                market=Market.US,
                trade_date=None,  # 美股交易日期需要单独获取
            )
            
            market_cache.set(cache_key, quote, cache_type="quote")
            return quote
        except Exception as e:
            logger.error(f"获取美股行情失败 | symbol={symbol} | error={e}")
            return None


# 全局客户端实例（延迟初始化）
_client: Optional[AKShareClient] = None


def get_client() -> AKShareClient:
    """获取 AKShare 客户端单例"""
    global _client
    if _client is None:
        _client = AKShareClient()
    return _client
