"""
Data Loader - 回测数据加载器

从本地数据库加载真实历史数据，支持自动补充缺失数据
"""
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestDataLoader:
    """
    回测数据加载器
    
    优先从 SQLite 数据库加载历史数据
    如果数据缺失，自动从 AKShare 补充
    """
    
    def __init__(self, data_service=None):
        """
        初始化数据加载器
        
        Args:
            data_service: DataService 实例（可选）
        """
        self.data_service = data_service
        self._ak = None
    
    def _get_ak(self):
        """延迟加载 AKShare"""
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak
    
    def load_klines(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        加载 K 线数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            period: 周期（daily/weekly/monthly）
            adjust: 复权类型（qfq/hfq/none）
            
        Returns:
            DataFrame 包含 OHLCV 数据
        """
        logger.info(f"加载数据 | symbol={symbol}, start={start_date}, end={end_date}")
        
        # 1. 尝试从数据库加载
        df = self._load_from_db(symbol, start_date, end_date, period)
        
        # 2. 如果数据不足，从 AKShare 补充
        if len(df) < self._expected_days(start_date, end_date) * 0.8:
            logger.info(f"数据库数据不足，从 AKShare 补充 | symbol={symbol}")
            df_ak = self._load_from_akshare(symbol, start_date, end_date, period, adjust)
            
            # 合并数据（数据库 + 新数据）
            if not df.empty and not df_ak.empty:
                df = pd.concat([df, df_ak]).drop_duplicates(subset=['date'], keep='last')
            elif not df_ak.empty:
                df = df_ak
        
        # 3. 数据排序和索引
        if not df.empty:
            df = df.sort_values('date')
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        logger.info(f"数据加载完成 | symbol={symbol}, rows={len(df)}")
        return df
    
    def _load_from_db(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str
    ) -> pd.DataFrame:
        """从数据库加载"""
        try:
            if self.data_service:
                # 使用 DataService
                klines = self.data_service.db.get_kline(
                    symbol, period, start_date, end_date
                )
                if klines:
                    df = pd.DataFrame(klines)
                    logger.debug(f"从数据库加载 | symbol={symbol}, rows={len(df)}")
                    return df
        except Exception as e:
            logger.warning(f"数据库加载失败 | symbol={symbol}, error={e}")
        
        return pd.DataFrame()
    
    def _load_from_akshare(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str,
        adjust: str
    ) -> pd.DataFrame:
        """从 AKShare 加载"""
        try:
            ak = self._get_ak()
            
            # 调整日期格式
            start = start_date.replace('-', '')
            end = end_date.replace('-', '')
            
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                adjust=adjust
            )
            
            if df.empty:
                logger.warning(f"AKShare 无数据 | symbol={symbol}")
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'turnover',
                '涨跌幅': 'change_percent'
            })
            
            # 选择需要的列
            columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'change_percent']
            df = df[[c for c in columns if c in df.columns]]
            
            logger.debug(f"从 AKShare 加载 | symbol={symbol}, rows={len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"AKShare 加载失败 | symbol={symbol}, error={e}")
            return pd.DataFrame()
    
    def _expected_days(self, start_date: str, end_date: str) -> int:
        """估算预期交易日天数"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        total_days = (end - start).days
        
        # 约 250 个交易日/年
        return int(total_days * 250 / 365)
    
    def get_trading_calendar(
        self,
        start_date: str,
        end_date: str,
        market: str = "A"
    ) -> pd.DatetimeIndex:
        """
        获取交易日历
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            market: 市场类型
            
        Returns:
            DatetimeIndex 包含所有交易日
        """
        # 简单实现：排除周末
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
        return dates


# 全局实例
_data_loader: Optional[BacktestDataLoader] = None


def get_data_loader(data_service=None) -> BacktestDataLoader:
    """获取数据加载器实例"""
    global _data_loader
    if _data_loader is None:
        _data_loader = BacktestDataLoader(data_service)
    return _data_loader
