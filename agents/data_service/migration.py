"""
Database Migration - 数据库迁移脚本

添加数据覆盖范围表（data_coverage）
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)


def migrate_to_v2(db_path: str):
    """
    迁移到 v2 版本：添加数据覆盖范围表
    
    Args:
        db_path: 数据库文件路径
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 检查是否已存在 data_coverage 表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='data_coverage'
        """)
        
        if cursor.fetchone():
            logger.info("data_coverage 表已存在，跳过迁移")
            return
        
        # 2. 创建数据覆盖范围表
        logger.info("创建 data_coverage 表...")
        cursor.execute("""
            CREATE TABLE data_coverage (
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
        
        # 3. 创建索引
        logger.info("创建索引...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_symbol_freq 
            ON data_coverage(symbol, frequency)
        """)
        
        # 4. 从现有 klines 数据初始化覆盖范围
        logger.info("从现有数据初始化覆盖范围...")
        cursor.execute("""
            INSERT OR REPLACE INTO data_coverage 
            (symbol, frequency, start_date, end_date, record_count, completeness)
            SELECT 
                symbol,
                period as frequency,
                MIN(date) as start_date,
                MAX(date) as end_date,
                COUNT(*) as record_count,
                1.0 as completeness
            FROM klines
            GROUP BY symbol, period
        """)
        
        # 5. 更新 klines 表的索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_klines_symbol_freq_date 
            ON klines(symbol, frequency, date)
        """)
        
        # 6. 记录迁移版本
        cursor.execute("""
            INSERT OR REPLACE INTO sync_meta (key, value, updated_at)
            VALUES ('db_version', '2', CURRENT_TIMESTAMP)
        """)
        
        conn.commit()
        
        # 7. 统计迁移结果
        cursor.execute("SELECT COUNT(*) FROM data_coverage")
        coverage_count = cursor.fetchone()[0]
        
        logger.info(f"✅ 迁移完成 | 覆盖范围记录：{coverage_count}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 迁移失败 | error={e}")
        raise
    
    finally:
        conn.close()


def verify_migration(db_path: str) -> bool:
    """
    验证迁移是否成功
    
    Args:
        db_path: 数据库文件路径
        
    Returns:
        是否成功
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='data_coverage'
        """)
        
        if not cursor.fetchone():
            return False
        
        # 检查索引是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_coverage_symbol_freq'
        """)
        
        if not cursor.fetchone():
            return False
        
        # 检查是否有数据
        cursor.execute("SELECT COUNT(*) FROM data_coverage")
        count = cursor.fetchone()[0]
        
        logger.info(f"✅ 验证通过 | data_coverage 记录数：{count}")
        return count > 0
        
    except Exception as e:
        logger.error(f"❌ 验证失败 | error={e}")
        return False
    
    finally:
        conn.close()


if __name__ == "__main__":
    # 执行迁移
    db_path = "data/stock_data.db"
    
    logger.info("=" * 60)
    logger.info("数据库迁移 v1 → v2")
    logger.info("=" * 60)
    
    migrate_to_v2(db_path)
    
    if verify_migration(db_path):
        logger.info("✅ 迁移成功！")
    else:
        logger.error("❌ 迁移失败！")
