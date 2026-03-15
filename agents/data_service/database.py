"""
Database - SQLite 数据存储

存储历史 K 线、股票列表等持久化数据
"""
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class StockDatabase:
    """
    股票数据库
    
    表结构：
    - stocks: 股票列表
    - klines: K 线数据
    - quotes: 行情快照（可选）
    - sync_log: 同步日志
    """
    
    def __init__(self, db_path: str):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_tables()
        logger.debug(f"数据库初始化 | path={db_path}")
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_tables(self):
        """初始化数据库表"""
        with self.get_cursor() as cursor:
            # 股票列表表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    market TEXT NOT NULL,
                    list_date TEXT,
                    industry TEXT,
                    area TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # K 线数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS klines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    period TEXT NOT NULL DEFAULT 'daily',
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    turnover REAL,
                    change_percent REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, period, date)
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_klines_symbol_date 
                ON klines(symbol, period, date)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_stocks_market 
                ON stocks(market)
            """)
            
            # 同步日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT NOT NULL,
                    symbol TEXT,
                    records_count INTEGER,
                    status TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 最后同步时间表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("数据库表初始化完成")
    
    # ==================== 股票列表 ====================
    
    def save_stock_list(self, stocks: List[Dict]):
        """
        保存股票列表
        
        Args:
            stocks: 股票列表
        """
        with self.get_cursor() as cursor:
            for stock in stocks:
                cursor.execute("""
                    INSERT OR REPLACE INTO stocks 
                    (symbol, name, market, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    stock.get('symbol'),
                    stock.get('name'),
                    stock.get('market', 'A')
                ))
            
            # 更新同步时间
            cursor.execute("""
                INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
                VALUES ('stock_list_sync', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """)
            
            logger.info(f"股票列表已保存 | count={len(stocks)}")
    
    def get_stock_list(self, market: str = "A") -> List[Dict]:
        """
        获取股票列表
        
        Args:
            market: 市场类型
            
        Returns:
            股票列表
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT symbol, name, market, list_date, industry, area
                FROM stocks
                WHERE market = ?
                ORDER BY symbol
            """, (market,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stock_count(self) -> int:
        """获取股票总数"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM stocks")
            return cursor.fetchone()[0]
    
    def is_stock_list_old(self, days: int = 7) -> bool:
        """
        检查股票列表是否过期
        
        Args:
            days: 过期天数
            
        Returns:
            是否过期
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT value FROM sync_meta 
                WHERE key = 'stock_list_sync'
            """)
            row = cursor.fetchone()
            
            if not row:
                return True
            
            last_sync = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f" if "." in row[0] else "%Y-%m-%d %H:%M:%S")
            return datetime.now() - last_sync > timedelta(days=days)
    
    def search_stock(self, keyword: str, market: str = "A", limit: int = 10) -> List[Dict]:
        """
        搜索股票
        
        Args:
            keyword: 关键词
            market: 市场类型
            limit: 返回数量
            
        Returns:
            搜索结果
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT symbol, name, market
                FROM stocks
                WHERE market = ?
                AND (symbol LIKE ? OR name LIKE ?)
                ORDER BY symbol
                LIMIT ?
            """, (market, f"%{keyword}%", f"%{keyword}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== K 线数据 ====================
    
    def save_kline(self, symbol: str, period: str, klines: List[Dict]):
        """
        保存 K 线数据
        
        Args:
            symbol: 股票代码
            period: 周期
            klines: K 线数据列表
        """
        with self.get_cursor() as cursor:
            for kline in klines:
                cursor.execute("""
                    INSERT OR REPLACE INTO klines 
                    (symbol, period, date, open, high, low, close, volume, turnover, change_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    period,
                    kline.get('date'),
                    kline.get('open', 0),
                    kline.get('high', 0),
                    kline.get('low', 0),
                    kline.get('close', 0),
                    kline.get('volume', 0),
                    kline.get('turnover'),
                    kline.get('change_percent')
                ))
            
            logger.debug(f"K 线已保存 | symbol={symbol} | period={period} | count={len(klines)}")
    
    def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: int = 100
    ) -> List[Dict]:
        """
        获取 K 线数据
        
        Args:
            symbol: 股票代码
            period: 周期
            start_date: 开始日期
            end_date: 结束日期
            count: 返回条数
            
        Returns:
            K 线数据列表
        """
        with self.get_cursor() as cursor:
            if start_date and end_date:
                cursor.execute("""
                    SELECT date, open, high, low, close, volume, turnover, change_percent
                    FROM klines
                    WHERE symbol = ? AND period = ?
                    AND date >= ? AND date <= ?
                    ORDER BY date
                """, (symbol, period, start_date, end_date))
            else:
                cursor.execute("""
                    SELECT date, open, high, low, close, volume, turnover, change_percent
                    FROM klines
                    WHERE symbol = ? AND period = ?
                    ORDER BY date DESC
                    LIMIT ?
                """, (symbol, period, count))
            
            rows = cursor.fetchall()
            
            # 如果是按日期范围查询，可能需要反转顺序
            if start_date and end_date:
                return [dict(row) for row in rows]
            else:
                # 按日期倒序查询后需要正序返回
                return [dict(row) for row in reversed(rows)]
    
    def get_kline_count(self) -> int:
        """获取 K 线总记录数"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM klines")
            return cursor.fetchone()[0]
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """
        获取最新的行情（从 K 线中获取）
        
        Args:
            symbol: 股票代码
            
        Returns:
            行情数据
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT date, open, high, low, close, volume, turnover, change_percent
                FROM klines
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 1
            """, (symbol,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "symbol": symbol,
                    "date": row['date'],
                    "close": row['close'],
                    "change_percent": row['change_percent']
                }
            return None
    
    # ==================== 同步日志 ====================
    
    def log_sync(self, sync_type: str, symbol: str = None, records: int = 0, status: str = "success", error: str = None):
        """
        记录同步日志
        
        Args:
            sync_type: 同步类型
            symbol: 股票代码
            records: 记录数
            status: 状态
            error: 错误信息
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO sync_log (sync_type, symbol, records_count, status, error)
                VALUES (?, ?, ?, ?, ?)
            """, (sync_type, symbol, records, status, error))
    
    def get_last_sync_time(self, sync_type: str = "all") -> Optional[str]:
        """
        获取最后同步时间
        
        Args:
            sync_type: 同步类型
            
        Returns:
            同步时间字符串
        """
        with self.get_cursor() as cursor:
            if sync_type == "all":
                cursor.execute("""
                    SELECT MAX(created_at) FROM sync_log WHERE status = 'success'
                """)
            else:
                cursor.execute("""
                    SELECT MAX(created_at) FROM sync_log 
                    WHERE sync_type = ? AND status = 'success'
                """, (sync_type,))
            
            row = cursor.fetchone()
            return row[0] if row else None
    
    # ==================== 清理 ====================
    
    def cleanup_old_klines(self, days: int = 365):
        """
        清理旧 K 线数据
        
        Args:
            days: 保留天数
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM klines WHERE date < ?
            """, (cutoff_date,))
            
            deleted = cursor.rowcount
            logger.info(f"清理旧 K 线数据 | deleted={deleted} | cutoff={cutoff_date}")
    
    def close(self):
        """关闭数据库连接"""
        # SQLite 连接在上下文管理器中已关闭
        logger.debug("数据库连接已关闭")
