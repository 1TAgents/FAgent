"""
Data Coverage Manager - 数据覆盖范围管理

核心功能：
1. 快速判断某只股票某频率的数据覆盖范围
2. 检查数据完整性
3. 计算缺失的日期范围
4. 更新覆盖范围统计
"""
import sqlite3
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CoverageManager:
    """
    数据覆盖范围管理器
    
    使用 data_coverage 表快速判断数据覆盖情况
    """
    
    def __init__(self, db_path: str):
        """
        初始化
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_table()
    
    def _ensure_table(self):
        """确保 data_coverage 表存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                frequency TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                record_count INTEGER NOT NULL,
                completeness REAL DEFAULT 1.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(symbol, frequency)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_symbol_freq 
            ON data_coverage(symbol, frequency)
        """)
        
        conn.commit()
        conn.close()
    
    def get_coverage(
        self, 
        symbol: str, 
        frequency: str = "daily"
    ) -> Optional[Dict]:
        """
        获取数据覆盖范围
        
        Args:
            symbol: 股票代码
            frequency: 频率（daily/weekly/monthly）
            
        Returns:
            覆盖范围信息，不存在则返回 None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, frequency, start_date, end_date, 
                   record_count, completeness, last_updated
            FROM data_coverage
            WHERE symbol = ? AND frequency = ?
        """, (symbol, frequency))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'symbol': row['symbol'],
                'frequency': row['frequency'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'record_count': row['record_count'],
                'completeness': row['completeness'],
                'last_updated': row['last_updated']
            }
        
        return None
    
    def should_sync(
        self,
        symbol: str,
        frequency: str,
        start_date: str,
        end_date: str,
        completeness_threshold: float = 0.95
    ) -> Tuple[bool, str]:
        """
        判断是否需要同步
        
        Args:
            symbol: 股票代码
            frequency: 频率
            start_date: 请求开始日期
            end_date: 请求结束日期
            completeness_threshold: 完整度阈值（默认 95%）
            
        Returns:
            (是否需要同步，原因)
        """
        coverage = self.get_coverage(symbol, frequency)
        
        if not coverage:
            return True, "从未同步过"
        
        # 检查请求范围是否完全在覆盖范围内
        if (coverage['start_date'] <= start_date and 
            coverage['end_date'] >= end_date):
            
            if coverage['completeness'] >= completeness_threshold:
                return False, f"数据已完整 ({coverage['completeness']:.1%})"
            else:
                return True, f"完整度不足 ({coverage['completeness']:.1%})"
        
        # 部分覆盖或完全未覆盖
        return True, "部分覆盖或完全未覆盖"
    
    def calculate_missing_ranges(
        self,
        symbol: str,
        frequency: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        计算缺失的日期范围
        
        Args:
            symbol: 股票代码
            frequency: 频率
            start_date: 请求开始日期
            end_date: 请求结束日期
            
        Returns:
            缺失范围列表
        """
        coverage = self.get_coverage(symbol, frequency)
        
        if not coverage:
            # 从未同步过，返回完整范围
            return [{'start': start_date, 'end': end_date}]
        
        missing_ranges = []
        
        # 检查是否有前置缺失
        if coverage['start_date'] > start_date:
            missing_ranges.append({
                'start': start_date,
                'end': min(coverage['start_date'], end_date)
            })
        
        # 检查是否有后置缺失
        if coverage['end_date'] < end_date:
            missing_ranges.append({
                'start': max(coverage['end_date'], start_date),
                'end': end_date
            })
        
        return missing_ranges
    
    def update_coverage(
        self,
        symbol: str,
        frequency: str,
        start_date: str,
        end_date: str,
        record_count: int,
        completeness: float = 1.0
    ):
        """
        更新覆盖范围
        
        Args:
            symbol: 股票代码
            frequency: 频率
            start_date: 覆盖起始日期
            end_date: 覆盖结束日期
            record_count: 记录数
            completeness: 完整度
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("""
            SELECT start_date, end_date, record_count
            FROM data_coverage
            WHERE symbol = ? AND frequency = ?
        """, (symbol, frequency))
        
        existing = cursor.fetchone()
        
        if existing:
            # 合并覆盖范围
            new_start = min(existing[0], start_date)
            new_end = max(existing[1], end_date)
            new_count = existing[2] + record_count
            
            cursor.execute("""
                UPDATE data_coverage
                SET start_date = ?, end_date = ?, 
                    record_count = ?, completeness = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE symbol = ? AND frequency = ?
            """, (new_start, new_end, new_count, completeness, symbol, frequency))
        else:
            # 新建记录
            cursor.execute("""
                INSERT INTO data_coverage 
                (symbol, frequency, start_date, end_date, record_count, completeness)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, frequency, start_date, end_date, record_count, completeness))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"更新覆盖范围 | {symbol} {frequency} {start_date}~{end_date}")
    
    def refresh_coverage_from_klines(self, symbol: str, frequency: str = "daily"):
        """
        从 klines 表刷新覆盖范围统计
        
        Args:
            symbol: 股票代码
            frequency: 频率
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 统计 klines 表中的数据
        cursor.execute("""
            SELECT 
                MIN(date) as start_date,
                MAX(date) as end_date,
                COUNT(*) as record_count
            FROM klines
            WHERE symbol = ? AND period = ?
        """, (symbol, frequency))
        
        result = cursor.fetchone()
        
        if result[0]:  # 有数据
            self.update_coverage(
                symbol, frequency,
                result[0], result[1], result[2]
            )
        else:
            # 删除覆盖范围记录（没有数据）
            cursor.execute("""
                DELETE FROM data_coverage
                WHERE symbol = ? AND frequency = ?
            """, (symbol, frequency))
        
        conn.commit()
        conn.close()
    
    def get_all_coverage(self) -> List[Dict]:
        """
        获取所有覆盖范围
        
        Returns:
            覆盖范围列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, frequency, start_date, end_date, 
                   record_count, completeness, last_updated
            FROM data_coverage
            ORDER BY symbol, frequency
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_sync_stats(self) -> Dict:
        """
        获取同步统计
        
        Returns:
            统计信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总股票数
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM data_coverage")
        total_stocks = cursor.fetchone()[0]
        
        # 总记录数
        cursor.execute("SELECT SUM(record_count) FROM data_coverage")
        total_records = cursor.fetchone()[0] or 0
        
        # 平均完整度
        cursor.execute("SELECT AVG(completeness) FROM data_coverage")
        avg_completeness = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_stocks': total_stocks,
            'total_records': total_records,
            'avg_completeness': avg_completeness
        }
