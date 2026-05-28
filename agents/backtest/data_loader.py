"""
Data Loader - 回测数据加载器

从本地数据库加载真实历史数据，支持自动补充缺失数据
"""
import logging
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestDataLoader:
    """
    回测数据加载器
    
    优先从 SQLite 数据库加载历史数据
    如果数据缺失，优先从本地 QuantMInd 特征快照补充，再从 RQData/AKShare 补充
    """
    
    def __init__(self, data_service=None, quantmind_dir: Optional[str | Path] = None):
        """
        初始化数据加载器
        
        Args:
            data_service: DataService 实例（可选）
            quantmind_dir: QuantMInd 数据目录或 feature_snapshots 子目录（可选）
        """
        self.data_service = data_service
        self.quantmind_dir = self._resolve_quantmind_dir(quantmind_dir)
        self._rq = None
        self._ak = None
        self._init_rqdata()

    def _init_rqdata(self) -> None:
        """初始化 RQData（如果可用）。"""
        try:
            import rqdatac as rq

            rq.init()
            self._rq = rq
            logger.info("BacktestDataLoader 已启用 RQData 优先链路")
        except Exception as e:
            self._rq = None
            logger.warning(f"RQData 初始化失败，回退到本地库/AKShare | error={e}")

    def _get_ak(self):
        """延迟加载 AKShare"""
        if self._ak is None:
            import akshare as ak
            self._ak = ak
        return self._ak

    def _to_order_book_id(self, symbol: str) -> str:
        """将 A 股代码转换为 RQData order_book_id。"""
        code = symbol.strip()
        if code.endswith((".XSHG", ".XSHE")):
            return code
        if code.startswith(("6", "9")):
            return f"{code}.XSHG"
        return f"{code}.XSHE"
    
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
        
        min_rows = self._minimum_rows(start_date, end_date)

        # 1. 尝试从数据库加载
        df = self._load_from_db(symbol, start_date, end_date, period)

        # 2. 如果数据不足，从本地 QuantMInd parquet 快照补充
        if len(df) < min_rows and self.quantmind_dir is not None:
            logger.info(f"数据库数据不足，从 QuantMInd 快照补充 | symbol={symbol}")
            df_quantmind = self._load_from_quantmind(symbol, start_date, end_date, period)
            if not df.empty and not df_quantmind.empty:
                df = pd.concat([df, df_quantmind]).drop_duplicates(subset=["date"], keep="last")
            elif not df_quantmind.empty:
                df = df_quantmind
        
        # 3. 如果数据不足，优先从 RQData 补充
        if len(df) < min_rows:
            if period == "daily":
                logger.info(f"数据库数据不足，从 RQData 补充 | symbol={symbol}")
                df_rq = self._load_from_rqdata(symbol, start_date, end_date)
                if not df.empty and not df_rq.empty:
                    df = pd.concat([df, df_rq]).drop_duplicates(subset=["date"], keep="last")
                elif not df_rq.empty:
                    df = df_rq

        # 4. 如果仍然不足，再回退到 AKShare
        if len(df) < min_rows:
            logger.info(f"RQData/数据库数据不足，从 AKShare 补充 | symbol={symbol}")
            df_ak = self._load_from_akshare(symbol, start_date, end_date, period, adjust)

            # 合并数据（数据库 + 新数据）
            if not df.empty and not df_ak.empty:
                df = pd.concat([df, df_ak]).drop_duplicates(subset=['date'], keep='last')
            elif not df_ak.empty:
                df = df_ak

        # 5. 数据排序和索引
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

    def _load_from_quantmind(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str,
    ) -> pd.DataFrame:
        """从 QuantMInd feature_snapshots parquet 快照加载日线 OHLCV。"""
        if period != "daily" or self.quantmind_dir is None:
            return pd.DataFrame()

        try:
            symbols = self._quantmind_symbol_candidates(symbol)
            files = self._quantmind_files(start_date, end_date)
            frames = []

            for path in files:
                available_columns = self._parquet_columns(path)
                required_columns = ["symbol", "trade_date", "open", "high", "low", "close", "volume"]
                if not all(column in available_columns for column in required_columns):
                    logger.warning(f"QuantMInd 快照缺少 OHLCV 必需列 | file={path}")
                    continue

                optional_turnover = next(
                    (
                        column
                        for column in ("turnover", "amount", "liq_amount")
                        if column in available_columns
                    ),
                    None,
                )
                columns = required_columns + ([optional_turnover] if optional_turnover else [])
                frame = pd.read_parquet(
                    path,
                    columns=columns,
                    filters=[("symbol", "in", symbols)],
                )
                if not frame.empty:
                    frames.append(frame)

            if not frames:
                logger.warning(f"QuantMInd 无数据 | symbol={symbol}, range={start_date}~{end_date}")
                return pd.DataFrame()

            df = pd.concat(frames, ignore_index=True)
            df = df.rename(
                columns={
                    "trade_date": "date",
                    "amount": "turnover",
                    "liq_amount": "turnover",
                }
            )
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            df = df[(df["date"] >= start) & (df["date"] <= end)]
            for column in ["open", "high", "low", "close", "volume", "turnover"]:
                if column in df.columns:
                    df[column] = pd.to_numeric(df[column], errors="coerce")

            df = df.dropna(subset=["date", "open", "high", "low", "close"])
            df["date"] = df["date"].dt.strftime("%Y-%m-%d")
            df = df.sort_values(["date", "symbol"]).drop_duplicates(subset=["date"], keep="last")

            columns = ["date", "symbol", "open", "high", "low", "close", "volume", "turnover"]
            df = df[[column for column in columns if column in df.columns]]
            logger.debug(f"从 QuantMInd 加载 | symbol={symbol}, rows={len(df)}")
            return df

        except Exception as e:
            logger.warning(f"QuantMInd 加载失败 | symbol={symbol}, error={e}")
            return pd.DataFrame()

    def _load_from_rqdata(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """从 RQData 加载前复权日线。"""
        if self._rq is None:
            return pd.DataFrame()

        try:
            df = self._rq.get_price(
                order_book_ids=self._to_order_book_id(symbol),
                start_date=start_date,
                end_date=end_date,
                frequency="1d",
                adjust_type="pre",
            )

            if df is None or df.empty:
                logger.warning(f"RQData 无数据 | symbol={symbol}")
                return pd.DataFrame()

            df = df.reset_index()
            if "date" not in df.columns:
                first_col = df.columns[0]
                df = df.rename(columns={first_col: "date"})

            if "turnover" not in df.columns and "total_turnover" in df.columns:
                df = df.rename(columns={"total_turnover": "turnover"})

            df["symbol"] = symbol
            keep_columns = [
                "date",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "turnover",
            ]
            df = df[[col for col in keep_columns if col in df.columns]]

            logger.debug(f"从 RQData 加载 | symbol={symbol}, rows={len(df)}")
            return df
        except Exception as e:
            logger.warning(f"RQData 加载失败 | symbol={symbol}, error={e}")
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

    def _minimum_rows(self, start_date: str, end_date: str) -> int:
        """估算足够覆盖一个回测区间的最低行数。"""
        return max(1, int(self._expected_days(start_date, end_date) * 0.8))

    def _resolve_quantmind_dir(self, quantmind_dir: Optional[str | Path]) -> Optional[Path]:
        """解析 QuantMInd feature_snapshots 目录。"""
        candidates = []
        if quantmind_dir:
            candidates.append(Path(quantmind_dir))

        for env_name in ("BACKTEST_QUANTMIND_DATA_DIR", "QUANTMIND_DATA_DIR"):
            env_value = os.environ.get(env_name)
            if env_value:
                candidates.append(Path(env_value))

        candidates.extend([
            Path.home() / "Learning" / "quant_repos" / "data" / "QuantMInd",
            Path.home() / "Learning" / "quant_repos" / "data" / "QuantMInd" / "feature_snapshots",
        ])

        seen = set()
        for candidate in candidates:
            path = candidate.expanduser()
            if path in seen:
                continue
            seen.add(path)
            if (path / "feature_snapshots").is_dir():
                path = path / "feature_snapshots"
            if path.is_dir() and any(path.glob("model_features_*.parquet")):
                logger.info(f"BacktestDataLoader 已启用 QuantMInd 本地数据 | dir={path}")
                return path

        return None

    def _quantmind_files(self, start_date: str, end_date: str) -> List[Path]:
        """返回日期区间覆盖到的 QuantMInd 年度 parquet 文件。"""
        if self.quantmind_dir is None:
            return []

        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        files = []
        for year in range(start.year, end.year + 1):
            path = self.quantmind_dir / f"model_features_{year}.parquet"
            if path.exists():
                files.append(path)
        return files

    def _quantmind_symbol_candidates(self, symbol: str) -> List[str]:
        """生成 QuantMInd 使用的 SH/SZ 前缀股票代码候选。"""
        raw = symbol.strip().upper()
        raw = raw.replace(".XSHG", "").replace(".XSHE", "")

        if raw.endswith(".SH"):
            raw = f"SH{raw[:-3]}"
        elif raw.endswith(".SZ"):
            raw = f"SZ{raw[:-3]}"

        candidates = []
        if raw.startswith(("SH", "SZ")):
            candidates.append(raw)
        elif raw.startswith(("6", "9")):
            candidates.append(f"SH{raw}")
        elif raw.startswith(("0", "3")):
            candidates.append(f"SZ{raw}")
        else:
            candidates.extend([f"SH{raw}", f"SZ{raw}"])

        if raw not in candidates:
            candidates.append(raw)

        return candidates

    def _parquet_columns(self, path: Path) -> set:
        """读取 parquet schema 列名，避免为探测列名加载全表。"""
        try:
            import pyarrow.parquet as pq

            return set(pq.ParquetFile(path).schema.names)
        except Exception:
            return set(pd.read_parquet(path).columns)
    
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
