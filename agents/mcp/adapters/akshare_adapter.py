"""
AKShare Adapter - AKShare 数据源适配器

参考文档：https://akshare.akfamily.xyz/

实现 MCP 工具的标准接口，将 AKShare 数据转换为统一格式
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ..models import (
    StockQuote, KLineData, KLineItem, StockInfo, 
    MarketType, KLinePeriod, IndexQuote, IndustryQuote, IndustryDetail
)
from .cache_adapter import CacheAdapter, get_mcp_cache

logger = logging.getLogger(__name__)


class AKShareAdapter:
    """
    AKShare 数据源适配器
    
    将 AKShare 的 API 转换为 MCP 标准工具接口
    
    Args:
        redis_url: Redis 连接 URL（可选，启用缓存）
        cache_enabled: 是否启用缓存
    """
    
    def __init__(self, redis_url: str = None, cache_enabled: bool = True):
        self._ak = None
        self._cache: CacheAdapter = None
        self._init_akshare()
        self._init_cache(redis_url, cache_enabled)
    
    def _init_akshare(self):
        """延迟加载 akshare"""
        try:
            import akshare as ak
            self._ak = ak
            logger.info("AKShare Adapter 初始化成功")
        except ImportError:
            logger.error("AKShare 未安装，请执行：pip install akshare")
            raise ImportError("请安装 akshare: pip install akshare")
    
    def _init_cache(self, redis_url: str = None, cache_enabled: bool = True):
        """初始化缓存"""
        if cache_enabled:
            url = redis_url or "redis://localhost:6379"
            self._cache = CacheAdapter(redis_url=url, enabled=True)
            logger.info(f"MCP 缓存已启用 | redis_url={url}")
        else:
            self._cache = None
            logger.info("MCP 缓存已禁用")
    
    @property
    def ak(self):
        """获取 akshare 模块"""
        if self._ak is None:
            self._init_akshare()
        return self._ak
    
    # ==================== 工具：实时行情 ====================
    
    async def get_quote(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """
        获取实时行情（带缓存）
        
        Args:
            symbol: 股票代码 (如：600519, AAPL)
            market: 市场类型 (A=A 股，US=美股，HK=港股)
            
        Returns:
            StockQuote 字典格式
            
        Examples:
            >>> await adapter.get_quote("600519", "A")
            {"symbol": "600519", "name": "贵州茅台", "price": 1700.00, ...}
        """
        # 1. 尝试从缓存获取
        if self._cache:
            cached = await self._cache.get_quote(symbol, market)
            if cached:
                logger.info(f"行情缓存命中 | symbol={symbol} | market={market}")
                return cached
        
        # 2. 缓存未命中，调用 API
        try:
            market_type = MarketType(market)
            
            if market_type == MarketType.A_SHARE:
                result = await self._get_a_share_quote(symbol)
            elif market_type == MarketType.US:
                result = await self._get_us_stock_quote(symbol)
            elif market_type == MarketType.HK:
                return await self._get_hk_stock_quote(symbol)
            else:
                raise ValueError(f"不支持的市场类型：{market}")
            
            # 3. 写入缓存（行情默认 60 秒）
            if self._cache and result:
                await self._cache.set_quote(symbol, result, ttl=60)
            
            return result
                
        except Exception as e:
            logger.error(f"获取行情失败 | symbol={symbol} | market={market} | error={e}")
            raise
    
    async def _get_a_share_quote(self, symbol: str) -> Dict[str, Any]:
        """获取 A 股行情"""
        # 使用更快的单股票接口
        df = self.ak.stock_individual_info_em(symbol=symbol)
        
        # 解析数据
        quote_dict = {}
        for _, row in df.iterrows():
            if len(row) >= 2:
                key = str(row.iloc[0])
                value = row.iloc[1]
                quote_dict[key] = value
        
        # 提取关键字段
        try:
            # 获取实时行情数据
            quote_df = self.ak.stock_zh_a_spot_em()
            stock_data = quote_df[quote_df['代码'] == symbol]
            
            if stock_data.empty:
                raise ValueError(f"未找到股票：{symbol}")
            
            row = stock_data.iloc[0]
            
            result = {
                "symbol": symbol,
                "name": row.get('名称', ''),
                "market": MarketType.A_SHARE.value,
                "price": float(row.get('最新价', 0)),
                "open": float(row.get('今开', 0)),
                "high": float(row.get('最高', 0)),
                "low": float(row.get('最低', 0)),
                "close": float(row.get('昨收', 0)),
                "change": float(row.get('涨跌额', 0)),
                "change_percent": float(row.get('涨跌幅', 0)),
                "volume": int(float(row.get('成交量', 0)) * 100),  # 手→股
                "turnover": float(row.get('成交额', 0)),
                "amount": float(row.get('成交额', 0)) / 10000,  # 元→万元
                "pe_ratio": float(row.get('市盈率 - 动态', 0)) if row.get('市盈率 - 动态') else None,
                "pb_ratio": float(row.get('市净率', 0)) if row.get('市净率') else None,
                "total_market_cap": float(row.get('总市值', 0)),
                "float_market_cap": float(row.get('流通市值', 0)),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.debug(f"A 股行情查询成功 | symbol={symbol} | price={result['price']}")
            return result
            
        except Exception as e:
            logger.error(f"A 股行情解析失败 | symbol={symbol} | error={e}")
            raise
    
    async def _get_us_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """获取美股行情"""
        try:
            # 获取美股实时行情
            quote_df = self.ak.stock_us_spot_em()
            stock_data = quote_df[quote_df['代码'] == symbol]
            
            if stock_data.empty:
                raise ValueError(f"未找到美股：{symbol}")
            
            row = stock_data.iloc[0]
            
            result = {
                "symbol": symbol,
                "name": row.get('名称', ''),
                "market": MarketType.US.value,
                "price": float(row.get('最新价', 0)),
                "open": float(row.get('今开', 0)),
                "high": float(row.get('最高', 0)),
                "low": float(row.get('最低', 0)),
                "close": float(row.get('昨收', 0)),
                "change": float(row.get('涨跌额', 0)),
                "change_percent": float(row.get('涨跌幅', 0)),
                "volume": int(float(row.get('成交量', 0))),
                "turnover": 0.0,  # 美股 API 可能不提供
                "amount": 0.0,
                "pe_ratio": float(row.get('市盈率', 0)) if row.get('市盈率') else None,
                "pb_ratio": None,
                "total_market_cap": float(row.get('总市值', 0)) if row.get('总市值') else None,
                "float_market_cap": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.debug(f"美股行情查询成功 | symbol={symbol} | price={result['price']}")
            return result
            
        except Exception as e:
            logger.error(f"美股行情解析失败 | symbol={symbol} | error={e}")
            raise
    
    async def _get_hk_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """获取港股行情"""
        # TODO: 实现港股行情
        logger.warning(f"港股行情暂未支持 | symbol={symbol}")
        raise NotImplementedError("港股行情暂未支持")
    
    # ==================== 工具：K 线数据 ====================
    
    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        count: int = 100,
        market: str = "A",
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取 K 线数据（带缓存）
        
        Args:
            symbol: 股票代码
            period: 周期 (daily/weekly/monthly/1m/5m/15m/30m/60m)
            count: 返回条数
            market: 市场类型 (A=股，US=美股)
            
        Returns:
            K 线数据字典
        """
        # 1. 尝试从缓存获取
        if self._cache:
            cached = await self._cache.get_kline(symbol, period, count, market)
            if cached:
                logger.info(f"K 线缓存命中 | symbol={symbol} | period={period} | count={count}")
                return cached
        
        # 2. 缓存未命中，调用 API
        try:
            market_type = MarketType(market)
            
            if market_type == MarketType.A_SHARE:
                result = await self._get_a_share_kline(symbol, period, count, **kwargs)
            elif market_type == MarketType.US:
                result = await self._get_us_stock_kline(symbol, period, count, **kwargs)
            else:
                raise ValueError(f"不支持的市场类型：{market}")
            
            # 3. 写入缓存（K 线默认 300 秒）
            if self._cache and result:
                await self._cache.set_kline(symbol, period, count, result, ttl=300)
            
            return result
                
        except Exception as e:
            logger.error(f"获取 K 线失败 | symbol={symbol} | period={period} | error={e}")
            raise
    
    async def _get_a_share_kline(
        self,
        symbol: str,
        period: str = "daily",
        count: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """获取 A 股 K 线"""
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=count * 2)  # 预留非交易日
            
            df = self.ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                raise ValueError(f"无 K 线数据：{symbol}")
            
            # 取最近 count 条
            df = df.tail(count)
            
            # 转换为 KLineItem 列表
            items = []
            for _, row in df.iterrows():
                item = KLineItem(
                    date=str(row.get('日期', '')),
                    open=float(row.get('开盘', 0)),
                    high=float(row.get('最高', 0)),
                    low=float(row.get('最低', 0)),
                    close=float(row.get('收盘', 0)),
                    volume=int(float(row.get('成交量', 0)) * 100),
                    turnover=float(row.get('成交额', 0)) if '成交额' in row else None,
                    change_percent=float(row.get('涨跌幅', 0)) if '涨跌幅' in row else None
                )
                items.append(item)
            
            # 获取股票名称
            name = self._get_stock_name(symbol)
            
            result = {
                "symbol": symbol,
                "name": name,
                "period": period,
                "items": [item.dict() for item in items]
            }
            
            logger.debug(f"A 股 K 线查询成功 | symbol={symbol} | count={len(items)}")
            return result
            
        except Exception as e:
            logger.error(f"A 股 K 线解析失败 | symbol={symbol} | error={e}")
            raise
    
    async def _get_us_stock_kline(
        self,
        symbol: str,
        period: str = "daily",
        count: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """获取美股 K 线"""
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=count * 2)
            
            df = self.ak.stock_us_hist(
                symbol=symbol,
                period=period,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq"
            )
            
            if df.empty:
                raise ValueError(f"无 K 线数据：{symbol}")
            
            df = df.tail(count)
            
            items = []
            for _, row in df.iterrows():
                item = KLineItem(
                    date=str(row.get('日期', '')),
                    open=float(row.get('开盘', 0)),
                    high=float(row.get('最高', 0)),
                    low=float(row.get('最低', 0)),
                    close=float(row.get('收盘', 0)),
                    volume=int(float(row.get('成交量', 0))),
                    turnover=None,
                    change_percent=float(row.get('涨跌幅', 0)) if '涨跌幅' in row else None
                )
                items.append(item)
            
            name = self._get_stock_name(symbol, market="US")
            
            result = {
                "symbol": symbol,
                "name": name,
                "period": period,
                "items": [item.dict() for item in items]
            }
            
            logger.debug(f"美股 K 线查询成功 | symbol={symbol} | count={len(items)}")
            return result
            
        except Exception as e:
            logger.error(f"美股 K 线解析失败 | symbol={symbol} | error={e}")
            raise
    
    # ==================== 工具：股票搜索 ====================
    
    async def search(self, keyword: str, market: str = "A", limit: int = 10) -> Dict[str, Any]:
        """
        搜索股票（带缓存）
        
        Args:
            keyword: 关键词（代码或名称）
            market: 市场类型
            limit: 返回数量
            
        Returns:
            搜索结果列表
        """
        # 1. 尝试从缓存获取
        if self._cache:
            cached = await self._cache.get_search(keyword, market, limit)
            if cached:
                logger.info(f"搜索缓存命中 | keyword={keyword} | market={market}")
                return cached
        
        # 2. 缓存未命中，调用 API
        try:
            market_type = MarketType(market)
            
            if market_type == MarketType.A_SHARE:
                result = await self._search_a_share(keyword, limit)
            elif market_type == MarketType.US:
                result = await self._search_us_stock(keyword, limit)
            else:
                raise ValueError(f"不支持的市场类型：{market}")
            
            # 3. 写入缓存（搜索默认 3600 秒）
            if self._cache and result:
                await self._cache.set_search(keyword, result, market, limit, ttl=3600)
            
            return result
                
        except Exception as e:
            logger.error(f"股票搜索失败 | keyword={keyword} | error={e}")
            raise
    
    async def _search_a_share(self, keyword: str, limit: int = 10) -> Dict[str, Any]:
        """搜索 A 股"""
        try:
            # 获取所有 A 股列表
            df = self.ak.stock_info_a_code_name()
            
            # 搜索（代码或名称）
            mask = df['code'].str.contains(keyword, na=False) | \
                   df['name'].str.contains(keyword, na=False)
            results = df[mask].head(limit)
            
            items = []
            for _, row in results.iterrows():
                item = {
                    "symbol": str(row.get('code', '')),
                    "name": str(row.get('name', '')),
                    "market": MarketType.A_SHARE.value
                }
                items.append(item)
            
            logger.debug(f"A 股搜索成功 | keyword={keyword} | count={len(items)}")
            return {"items": items}
            
        except Exception as e:
            logger.error(f"A 股搜索失败 | keyword={keyword} | error={e}")
            raise
    
    async def _search_us_stock(self, keyword: str, limit: int = 10) -> Dict[str, Any]:
        """搜索美股"""
        try:
            # 获取美股列表
            df = self.ak.stock_us_spot_em()
            
            # 搜索
            mask = df['代码'].str.contains(keyword, na=False, case=False) | \
                   df['名称'].str.contains(keyword, na=False, case=False)
            results = df[mask].head(limit)
            
            items = []
            for _, row in results.iterrows():
                item = {
                    "symbol": str(row.get('代码', '')),
                    "name": str(row.get('名称', '')),
                    "market": MarketType.US.value
                }
                items.append(item)
            
            logger.debug(f"美股搜索成功 | keyword={keyword} | count={len(items)}")
            return {"items": items}
            
        except Exception as e:
            logger.error(f"美股搜索失败 | keyword={keyword} | error={e}")
            raise
    
    # ==================== 工具：资金流向 ====================
    
    async def get_fund_flow(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """
        获取资金流向
        
        Args:
            symbol: 股票代码
            market: 市场类型
            
        Returns:
            资金流向数据
        """
        try:
            if market == "A":
                # 获取个股资金流向
                df = self.ak.stock_individual_fund_flow(symbol=symbol)
                
                # 解析数据
                result = {
                    "symbol": symbol,
                    "market": market,
                    "main_force_in": float(df.iloc[-1].get('主力净流入 - 即时', 0)),
                    "main_force_out": float(df.iloc[-1].get('主力净流出 - 即时', 0)),
                    "retail_in": float(df.iloc[-1].get('散户净流入 - 即时', 0)),
                    "retail_out": float(df.iloc[-1].get('散户净流出 - 即时', 0)),
                }
                
                logger.debug(f"资金流向查询成功 | symbol={symbol}")
                return result
            else:
                logger.warning(f"暂不支持 {market} 市场的资金流向")
                return {"symbol": symbol, "market": market, "data": None}
                
        except Exception as e:
            logger.error(f"获取资金流向失败 | symbol={symbol} | error={e}")
            raise
    
    # ==================== 工具：股票排行 ====================
    
    async def get_stock_rank(
        self,
        rank_type: str = "gain",
        market: str = "A",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取股票排行榜
        
        Args:
            rank_type: 排行类型 (gain=涨幅，loss=跌幅，turnover=成交额，volume=成交量)
            market: 市场类型
            limit: 返回数量
            
        Returns:
            排行榜数据
        """
        try:
            if market == "A":
                if rank_type == "gain":
                    df = self.ak.stock_rank_cxg_em()
                elif rank_type == "loss":
                    df = self.ak.stock_rank_cxd_em()
                elif rank_type == "turnover":
                    df = self.ak.stock_rank_amt_em()
                elif rank_type == "volume":
                    df = self.ak.stock_rank_vol_em()
                else:
                    raise ValueError(f"未知的排行类型：{rank_type}")
                
                # 取前 limit 条
                df = df.head(limit)
                
                items = []
                for _, row in df.iterrows():
                    item = {
                        "symbol": str(row.get('代码', '')),
                        "name": str(row.get('名称', '')),
                        "price": float(row.get('最新价', 0)),
                        "change_percent": float(row.get('涨跌幅', 0)),
                        "volume": int(float(row.get('成交量', 0))),
                        "turnover": float(row.get('成交额', 0)),
                    }
                    items.append(item)
                
                result = {"rank_type": rank_type, "market": market, "items": items}
                logger.debug(f"股票排行查询成功 | type={rank_type} | count={len(items)}")
                return result
            else:
                logger.warning(f"暂不支持 {market} 市场的股票排行")
                return {"rank_type": rank_type, "market": market, "items": []}
                
        except Exception as e:
            logger.error(f"获取股票排行失败 | type={rank_type} | error={e}")
            raise
    
    # ==================== 工具：财务指标 ====================
    
    async def get_financial_indicator(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """
        获取财务指标
        
        Args:
            symbol: 股票代码
            market: 市场类型
            
        Returns:
            财务指标数据
        """
        try:
            if market == "A":
                # 获取财务指标
                df = self.ak.stock_financial_analysis_indicator(symbol=symbol)
                
                # 取最新一期数据
                if not df.empty:
                    latest = df.iloc[-1]
                    result = {
                        "symbol": symbol,
                        "market": market,
                        "date": str(latest.get('报告期', '')),
                        "pe_ratio": float(latest.get('市盈率', 0)) if latest.get('市盈率') else None,
                        "pb_ratio": float(latest.get('市净率', 0)) if latest.get('市净率') else None,
                        "roe": float(latest.get('净资产收益率 (%)', 0)) if latest.get('净资产收益率 (%)') else None,
                        "gross_margin": float(latest.get('销售毛利率 (%)', 0)) if latest.get('销售毛利率 (%)') else None,
                        "debt_ratio": float(latest.get('资产负债率 (%)', 0)) if latest.get('资产负债率 (%)') else None,
                    }
                    logger.debug(f"财务指标查询成功 | symbol={symbol}")
                    return result
                else:
                    return {"symbol": symbol, "market": market, "data": None}
            else:
                logger.warning(f"暂不支持 {market} 市场的财务指标")
                return {"symbol": symbol, "market": market, "data": None}
                
        except Exception as e:
            logger.error(f"获取财务指标失败 | symbol={symbol} | error={e}")
            raise
    
    # ==================== 辅助方法 ====================
    
    def _get_stock_name(self, symbol: str, market: str = "A") -> str:
        """获取股票名称"""
        try:
            if market == "A":
                df = self.ak.stock_info_a_code_name()
                result = df[df['code'] == symbol]
                if not result.empty:
                    return result.iloc[0]['name']
            elif market == "US":
                df = self.ak.stock_us_spot_em()
                result = df[df['代码'] == symbol]
                if not result.empty:
                    return result.iloc[0]['名称']
        except Exception as e:
            logger.warning(f"获取股票名称失败 | symbol={symbol} | error={e}")
        
        return ""
    
    # ==================== 工具：指数行情 ====================
    
    async def get_index_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取指数实时行情
        
        Args:
            symbol: 指数代码（如：000300, 000001, 399006）
            
        Returns:
            IndexQuote 字典格式
            
        Examples:
            >>> await adapter.get_index_quote("000300")
            {"symbol": "000300", "name": "沪深 300", "price": 3500.00, ...}
        """
        # 1. 尝试从缓存获取
        if self._cache:
            cached = await self._cache.get_index_quote(symbol)
            if cached:
                logger.info(f"指数行情缓存命中 | symbol={symbol}")
                return cached
        
        # 2. 缓存未命中，调用 API
        try:
            # 获取所有指数行情
            df = self.ak.stock_zh_index_spot_em()
            
            # 查找指定指数
            stock_data = df[df['代码'] == symbol]
            
            if stock_data.empty:
                raise ValueError(f"未找到指数：{symbol}")
            
            row = stock_data.iloc[0]
            
            result = {
                "symbol": symbol,
                "name": row.get('名称', ''),
                "price": float(row.get('最新价', 0)),
                "open": float(row.get('今开', 0)),
                "high": float(row.get('最高', 0)),
                "low": float(row.get('最低', 0)),
                "close": float(row.get('昨收', 0)),
                "change": float(row.get('涨跌额', 0)),
                "change_percent": float(row.get('涨跌幅', 0)),
                "volume": int(float(row.get('成交量', 0)) * 100),  # 手→股
                "turnover": float(row.get('成交额', 0)),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 3. 写入缓存（指数行情默认 60 秒）
            if self._cache and result:
                await self._cache.set_index_quote(symbol, result, ttl=60)
            
            logger.debug(f"指数行情查询成功 | symbol={symbol} | price={result['price']}")
            return result
                
        except Exception as e:
            logger.error(f"获取指数行情失败 | symbol={symbol} | error={e}")
            raise
    
    # ==================== 工具：指数 K 线 ====================
    
    async def get_index_kline(
        self,
        symbol: str,
        period: str = "daily",
        count: int = 100
    ) -> Dict[str, Any]:
        """
        获取指数 K 线数据
        
        Args:
            symbol: 指数代码
            period: 周期（daily/weekly/monthly）
            count: 返回条数
            
        Returns:
            K 线数据字典
        """
        # 1. 尝试从缓存获取
        if self._cache:
            cached = await self._cache.get_index_kline(symbol, period, count)
            if cached:
                logger.info(f"指数 K 线缓存命中 | symbol={symbol} | period={period}")
                return cached
        
        # 2. 缓存未命中，调用 API
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=count * 2)
            
            df = self.ak.stock_zh_index_daily_em(
                symbol=symbol,
                period=period,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            
            if df.empty:
                raise ValueError(f"无 K 线数据：{symbol}")
            
            df = df.tail(count)
            
            # 转换为 KLineItem 列表
            items = []
            for _, row in df.iterrows():
                item = KLineItem(
                    date=str(row.get('日期', '')),
                    open=float(row.get('开盘', 0)),
                    high=float(row.get('最高', 0)),
                    low=float(row.get('最低', 0)),
                    close=float(row.get('收盘', 0)),
                    volume=int(float(row.get('成交量', 0)) * 100),
                    turnover=float(row.get('成交额', 0)) if '成交额' in row else None,
                    change_percent=float(row.get('涨跌幅', 0)) if '涨跌幅' in row else None
                )
                items.append(item)
            
            # 获取指数名称
            name = self._get_index_name(symbol)
            
            result = {
                "symbol": symbol,
                "name": name,
                "period": period,
                "items": [item.dict() for item in items]
            }
            
            # 3. 写入缓存（K 线默认 300 秒）
            if self._cache and result:
                await self._cache.set_index_kline(symbol, period, count, result, ttl=300)
            
            logger.debug(f"指数 K 线查询成功 | symbol={symbol} | count={len(items)}")
            return result
                
        except Exception as e:
            logger.error(f"获取指数 K 线失败 | symbol={symbol} | period={period} | error={e}")
            raise
    
    # ==================== 工具：行业板块行情 ====================
    
    async def get_industry_quote(self, industry_name: str = None) -> Dict[str, Any]:
        """
        获取行业板块行情
        
        Args:
            industry_name: 行业名称（可选，不传则返回所有行业）
            
        Returns:
            行业行情数据（单个行业或行业列表）
            
        Examples:
            >>> await adapter.get_industry_quote()  # 所有行业
            >>> await adapter.get_industry_quote("半导体")  # 单个行业
        """
        try:
            # 获取所有行业板块
            df = self.ak.stock_board_industry_name_em()
            
            if industry_name:
                # 查询单个行业
                mask = df['板块名称'] == industry_name
                if not mask.any():
                    # 尝试模糊匹配
                    mask = df['板块名称'].str.contains(industry_name, na=False)
                df = df[mask]
                
                if df.empty:
                    raise ValueError(f"未找到行业：{industry_name}")
                
                row = df.iloc[0]
                result = {
                    "name": row.get('板块名称', ''),
                    "index_code": str(row.get('板块代码', '')),
                    "price": float(row.get('最新价', 0)),
                    "change": float(row.get('涨跌额', 0)),
                    "change_percent": float(row.get('涨跌幅', 0)),
                    "volume": int(float(row.get('成交量', 0)) * 100),
                    "turnover": float(row.get('成交额', 0)),
                    "lead_stock": None,
                    "lead_stock_symbol": None,
                    "lead_stock_change": None,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                logger.debug(f"行业行情查询成功 | industry={industry_name}")
                return result
            else:
                # 返回所有行业（按涨跌幅排序）
                df = df.sort_values('涨跌幅', ascending=False)
                
                items = []
                for _, row in df.iterrows():
                    item = {
                        "name": row.get('板块名称', ''),
                        "index_code": str(row.get('板块代码', '')),
                        "price": float(row.get('最新价', 0)),
                        "change": float(row.get('涨跌额', 0)),
                        "change_percent": float(row.get('涨跌幅', 0)),
                        "volume": int(float(row.get('成交量', 0)) * 100),
                        "turnover": float(row.get('成交额', 0)),
                    }
                    items.append(item)
                
                result = {"industries": items, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                logger.debug(f"行业板块查询成功 | count={len(items)}")
                return result
                
        except Exception as e:
            logger.error(f"获取行业板块失败 | industry={industry_name} | error={e}")
            raise
    
    # ==================== 工具：行业 K 线 ====================
    
    async def get_industry_kline(
        self,
        industry_name: str,
        period: str = "daily",
        count: int = 100
    ) -> Dict[str, Any]:
        """
        获取行业指数 K 线数据
        
        Args:
            industry_name: 行业名称（如：半导体、银行、医药）
            period: 周期（daily/weekly/monthly）
            count: 返回条数
            
        Returns:
            K 线数据字典
        """
        # 1. 尝试从缓存获取
        if self._cache:
            cached = await self._cache.get_industry_kline(industry_name, period, count)
            if cached:
                logger.info(f"行业 K 线缓存命中 | industry={industry_name}")
                return cached
        
        # 2. 缓存未命中，调用 API
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=count * 2)
            
            df = self.ak.stock_board_industry_hist_em(
                board=industry_name,
                period=period,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            
            if df.empty:
                raise ValueError(f"无 K 线数据：{industry_name}")
            
            df = df.tail(count)
            
            items = []
            for _, row in df.iterrows():
                item = KLineItem(
                    date=str(row.get('日期', '')),
                    open=float(row.get('开盘', 0)),
                    high=float(row.get('最高', 0)),
                    low=float(row.get('最低', 0)),
                    close=float(row.get('收盘', 0)),
                    volume=int(float(row.get('成交量', 0)) * 100),
                    turnover=float(row.get('成交额', 0)) if '成交额' in row else None,
                    change_percent=float(row.get('涨跌幅', 0)) if '涨跌幅' in row else None
                )
                items.append(item)
            
            result = {
                "industry_name": industry_name,
                "period": period,
                "items": [item.dict() for item in items]
            }
            
            # 3. 写入缓存
            if self._cache and result:
                await self._cache.set_industry_kline(industry_name, period, count, result, ttl=300)
            
            logger.debug(f"行业 K 线查询成功 | industry={industry_name} | count={len(items)}")
            return result
                
        except Exception as e:
            logger.error(f"获取行业 K 线失败 | industry={industry_name} | error={e}")
            raise
    
    # ==================== 工具：行业成分股 ====================
    
    async def get_industry_detail(self, industry_name: str) -> Dict[str, Any]:
        """
        获取行业成分股详情
        
        Args:
            industry_name: 行业名称
            
        Returns:
            行业成分股列表
        """
        # 1. 尝试从缓存获取
        if self._cache:
            cached = await self._cache.get_industry_detail(industry_name)
            if cached:
                logger.info(f"行业成分股缓存命中 | industry={industry_name}")
                return cached
        
        # 2. 缓存未命中，调用 API
        try:
            df = self.ak.stock_board_industry_cons_em(symbol=industry_name)
            
            if df.empty:
                raise ValueError(f"未找到行业：{industry_name}")
            
            stocks = []
            for _, row in df.iterrows():
                stock = {
                    "symbol": str(row.get('代码', '')),
                    "name": str(row.get('名称', '')),
                    "price": float(row.get('最新价', 0)) if '最新价' in row else None,
                    "change_percent": float(row.get('涨跌幅', 0)) if '涨跌幅' in row else None,
                    "weight": float(row.get('权重 (%)', 0)) if '权重 (%)' in row else None,
                }
                stocks.append(stock)
            
            # 获取行业代码
            index_code = ""
            board_df = self.ak.stock_board_industry_name_em()
            match = board_df[board_df['板块名称'] == industry_name]
            if not match.empty:
                index_code = str(match.iloc[0]['板块代码'])
            
            result = {
                "industry_name": industry_name,
                "index_code": index_code,
                "stock_count": len(stocks),
                "stocks": stocks,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 3. 写入缓存（成分股默认 3600 秒）
            if self._cache and result:
                await self._cache.set_industry_detail(industry_name, result, ttl=3600)
            
            logger.debug(f"行业成分股查询成功 | industry={industry_name} | count={len(stocks)}")
            return result
                
        except Exception as e:
            logger.error(f"获取行业成分股失败 | industry={industry_name} | error={e}")
            raise
    
    # ==================== 辅助方法：指数名称 ====================
    
    def _get_index_name(self, symbol: str) -> str:
        """获取指数名称"""
        try:
            df = self.ak.stock_zh_index_spot_em()
            result = df[df['代码'] == symbol]
            if not result.empty:
                return result.iloc[0]['名称']
        except Exception as e:
            logger.warning(f"获取指数名称失败 | symbol={symbol} | error={e}")
        
        return ""
    
    # ==================== 工具：龙虎榜 ====================
    
    async def get_stock_bill(self, date: str = None, symbol: str = None) -> Dict[str, Any]:
        """
        获取龙虎榜数据
        
        Args:
            date: 日期（YYYY-MM-DD 格式，不传则默认最近一个交易日）
            symbol: 股票代码（可选，不传则返回全市场龙虎榜）
            
        Returns:
            龙虎榜数据
            
        Examples:
            >>> await adapter.get_stock_bill()  # 全市场龙虎榜
            >>> await adapter.get_stock_bill(symbol="600519")  # 单只股票龙虎榜
        """
        try:
            if symbol:
                # 查询单只股票龙虎榜
                df = self.ak.stock_lhb_stock_detail_em(symbol=symbol)
                
                if df.empty:
                    return {"symbol": symbol, "items": [], "message": "无龙虎榜数据"}
                
                items = []
                for _, row in df.iterrows():
                    item = {
                        "trade_date": str(row.get('交易日期', '')),
                        "explanation": str(row.get('上榜原因', '')),
                        "buy_amount": float(row.get('买入金额', 0)) if '买入金额' in row else None,
                        "sell_amount": float(row.get('卖出金额', 0)) if '卖出金额' in row else None,
                        "net_amount": float(row.get('净买入额', 0)) if '净买入额' in row else None,
                    }
                    items.append(item)
                
                result = {"symbol": symbol, "items": items}
                logger.debug(f"个股龙虎榜查询成功 | symbol={symbol} | count={len(items)}")
                return result
            else:
                # 查询全市场龙虎榜（指定日期）
                query_date = date or datetime.now().strftime("%Y%m%d")
                df = self.ak.stock_lhb_detail_em(start_date=query_date, end_date=query_date)
                
                if df.empty:
                    return {"date": date, "items": [], "message": "无龙虎榜数据"}
                
                # 按股票分组
                grouped = df.groupby('代码')
                items = []
                for code, group in grouped.head(5).iterrows():  # 每只股票最多 5 条
                    row = group.iloc[0]
                    item = {
                        "symbol": str(row.get('代码', '')),
                        "name": str(row.get('名称', '')),
                        "close": float(row.get('收盘价', 0)),
                        "change_percent": float(row.get('涨跌幅', 0)),
                        "turnover": float(row.get('成交额', 0)),
                        "net_amount": float(row.get('净买入额', 0)) if '净买入额' in row else None,
                        "explanation": str(row.get('上榜原因', '')),
                    }
                    items.append(item)
                
                result = {"date": date or datetime.now().strftime("%Y-%m-%d"), "items": items}
                logger.debug(f"全市场龙虎榜查询成功 | date={date} | count={len(items)}")
                return result
                
        except Exception as e:
            logger.error(f"获取龙虎榜失败 | date={date}, symbol={symbol} | error={e}")
            raise
    
    # ==================== 工具：涨跌停统计 ====================
    
    async def get_limit_up_stats(self, date: str = None) -> Dict[str, Any]:
        """
        获取涨跌停池统计
        
        Args:
            date: 日期（YYYY-MM-DD 格式，不传则默认最近一个交易日）
            
        Returns:
            涨跌停统计
        """
        try:
            query_date = date or datetime.now().strftime("%Y%m%d")
            
            # 涨停池
            zt_df = self.ak.stock_zt_pool_em(date=query_date)
            zt_count = len(zt_df) if not zt_df.empty else 0
            
            # 跌停池
            dt_df = self.ak.stock_zt_pool_dt_em(date=query_date)
            dt_count = len(dt_df) if not dt_df.empty else 0
            
            # 涨停股池详情（前 20 只）
            zt_stocks = []
            if not zt_df.empty:
                for _, row in zt_df.head(20).iterrows():
                    zt_stocks.append({
                        "symbol": str(row.get('代码', '')),
                        "name": str(row.get('名称', '')),
                        "price": float(row.get('最新价', 0)),
                        "change_percent": float(row.get('涨跌幅', 0)),
                        "limit_up_reason": str(row.get('涨停原因', '')) if '涨停原因' in row else None,
                        "limit_up_time": str(row.get('首次涨停时间', '')) if '首次涨停时间' in row else None,
                    })
            
            result = {
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "limit_up_count": zt_count,
                "limit_down_count": dt_count,
                "limit_up_stocks": zt_stocks,
            }
            
            logger.debug(f"涨跌停统计查询成功 | date={date} | 涨停={zt_count}, 跌停={dt_count}")
            return result
                
        except Exception as e:
            logger.error(f"获取涨跌停统计失败 | date={date} | error={e}")
            raise
    
    # ==================== 工具：大宗交易 ====================
    
    async def get_block_trade(self, date: str = None, symbol: str = None) -> Dict[str, Any]:
        """
        获取大宗交易数据
        
        Args:
            date: 日期（YYYY-MM-DD 格式，不传则默认最近一个交易日）
            symbol: 股票代码（可选）
            
        Returns:
            大宗交易数据
        """
        try:
            query_date = date or datetime.now().strftime("%Y%m%d")
            
            if symbol:
                # 单只股票大宗交易
                df = self.ak.stock_block_trade_detail_em(symbol=symbol)
            else:
                # 全市场大宗交易
                df = self.ak.stock_block_trade_em(start_date=query_date, end_date=query_date)
            
            if df.empty:
                return {"date": date, "symbol": symbol, "items": [], "message": "无大宗交易数据"}
            
            items = []
            for _, row in df.head(50).iterrows():
                item = {
                    "symbol": str(row.get('证券代码', '')),
                    "name": str(row.get('证券简称', '')),
                    "trade_date": str(row.get('交易日期', '')),
                    "price": float(row.get('成交价', 0)),
                    "volume": int(float(row.get('成交量', 0))) if '成交量' in row else None,
                    "amount": float(row.get('成交额', 0)) if '成交额' in row else None,
                    "buyer": str(row.get('买方营业部', '')) if '买方营业部' in row else None,
                    "seller": str(row.get('卖方营业部', '')) if '卖方营业部' in row else None,
                }
                items.append(item)
            
            result = {
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "symbol": symbol,
                "items": items
            }
            
            logger.debug(f"大宗交易查询成功 | date={date}, symbol={symbol} | count={len(items)}")
            return result
                
        except Exception as e:
            logger.error(f"获取大宗交易失败 | date={date}, symbol={symbol} | error={e}")
            raise
    
    # ==================== 工具：融资融券 ====================
    
    async def get_margin_data(self, symbol: str = None, market: str = "SH", date: str = None) -> Dict[str, Any]:
        """
        获取融资融券数据
        
        Args:
            symbol: 股票代码（可选，不传则返回市场汇总）
            market: 市场（SH=上交所，SZ=深交所）
            date: 日期（可选）
            
        Returns:
            融资融券数据
        """
        try:
            if symbol:
                # 个股融资融券历史
                df = self.ak.stock_margin_underlying_info_szse(symbol=symbol)
                
                if df.empty:
                    return {"symbol": symbol, "items": [], "message": "无融资融券数据"}
                
                items = []
                for _, row in df.tail(20).iterrows():
                    item = {
                        "trade_date": str(row.get('交易日期', '')),
                        "financing_balance": float(row.get('融资余额', 0)) if '融资余额' in row else None,
                        "financing_buy": float(row.get('融资买入额', 0)) if '融资买入额' in row else None,
                        "securities_lending_balance": float(row.get('融券余量', 0)) if '融券余量' in row else None,
                        "securities_sell": float(row.get('融券卖出量', 0)) if '融券卖出量' in row else None,
                    }
                    items.append(item)
                
                result = {"symbol": symbol, "items": items}
                logger.debug(f"个股融资融券查询成功 | symbol={symbol} | count={len(items)}")
                return result
            else:
                # 市场融资融券汇总
                if market == "SH":
                    df = self.ak.stock_margin_sse(start_date=date or (datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                                                  end_date=date or datetime.now().strftime("%Y%m%d"))
                else:
                    df = self.ak.stock_margin_szse(start_date=date or (datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                                                   end_date=date or datetime.now().strftime("%Y%m%d"))
                
                if df.empty:
                    return {"market": market, "items": [], "message": "无融资融券数据"}
                
                items = []
                for _, row in df.tail(10).iterrows():
                    item = {
                        "trade_date": str(row.get('交易日期', '')),
                        "financing_balance": float(row.get('融资余额', 0)) if '融资余额' in row else None,
                        "securities_lending_balance": float(row.get('融券余额', 0)) if '融券余额' in row else None,
                        "total_balance": float(row.get('融资融券余额', 0)) if '融资融券余额' in row else None,
                    }
                    items.append(item)
                
                result = {"market": market, "items": items}
                logger.debug(f"市场融资融券查询成功 | market={market} | count={len(items)}")
                return result
                
        except Exception as e:
            logger.error(f"获取融资融券失败 | symbol={symbol}, market={market} | error={e}")
            raise
