"""
Market Cache - 行情数据缓存（SQLite 版）

功能：
- 内存缓存 + SQLite 持久化
- TTL 过期机制
- 按需加载，用到即缓存
"""

import sqlite3
import pickle
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Any
    created_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def remaining_seconds(self) -> int:
        """剩余有效时间"""
        expires_at = self.created_at + timedelta(seconds=self.ttl_seconds)
        remaining = (expires_at - datetime.now()).total_seconds()
        return max(0, int(remaining))


class MarketCache:
    """
    行情数据缓存（SQLite 持久化）
    
    特性：
    - 内存缓存，快速读取
    - SQLite 持久化，重启不丢失
    - TTL 过期机制
    - 线程安全
    - 按需加载
    """
    
    # 默认缓存时间（秒）
    DEFAULT_TTL = {
        "quote": 30,           # 实时行情缓存 30 秒
        "quote_all": 60,       # 全市场行情缓存 1 分钟
        "kline": 300,          # K线数据缓存 5 分钟
        "search": 3600,        # 搜索结果缓存 1 小时
    }
    
    def __init__(self, db_path: str = "data/market_cache.db"):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        
        # 从数据库加载缓存
        self._load_from_db()
        
        logger.info(f"MarketCache 初始化完成 | db={self._db_path}")
    
    # ==================== 数据库操作 ====================
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    ttl_seconds INTEGER NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)")
            conn.commit()
    
    def _save_to_db(self, key: str, entry: CacheEntry):
        """保存到数据库"""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache (key, data, created_at, ttl_seconds)
                    VALUES (?, ?, ?, ?)
                """, (
                    key,
                    pickle.dumps(entry.data),
                    entry.created_at.isoformat(),
                    entry.ttl_seconds,
                ))
                conn.commit()
            logger.debug(f"缓存已持久化 | key={key}")
        except Exception as e:
            logger.error(f"缓存持久化失败 | key={key} | error={e}")
    
    def _load_from_db(self):
        """从数据库加载所有有效缓存"""
        try:
            with self._get_conn() as conn:
                rows = conn.execute("SELECT key, data, created_at, ttl_seconds FROM cache").fetchall()
            
            loaded = 0
            expired = 0
            for row in rows:
                created_at = datetime.fromisoformat(row["created_at"])
                entry = CacheEntry(
                    data=pickle.loads(row["data"]),
                    created_at=created_at,
                    ttl_seconds=row["ttl_seconds"],
                )
                
                if not entry.is_expired():
                    with self._lock:
                        self._cache[row["key"]] = entry
                    loaded += 1
                else:
                    expired += 1
            
            # 清理过期数据
            if expired > 0:
                self._cleanup_expired_db()
            
            logger.info(f"从数据库加载缓存 | loaded={loaded} | expired={expired}")
        except Exception as e:
            logger.error(f"加载数据库缓存失败 | error={e}")
    
    def _delete_from_db(self, key: str):
        """从数据库删除"""
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
        except Exception as e:
            logger.error(f"删除数据库缓存失败 | key={key} | error={e}")
    
    def _cleanup_expired_db(self):
        """清理数据库中的过期数据"""
        try:
            with self._get_conn() as conn:
                # 获取所有记录检查过期
                rows = conn.execute("SELECT key, created_at, ttl_seconds FROM cache").fetchall()
                expired_keys = []
                
                for row in rows:
                    created_at = datetime.fromisoformat(row["created_at"])
                    expires_at = created_at + timedelta(seconds=row["ttl_seconds"])
                    if datetime.now() > expires_at:
                        expired_keys.append(row["key"])
                
                if expired_keys:
                    conn.executemany(
                        "DELETE FROM cache WHERE key = ?",
                        [(k,) for k in expired_keys]
                    )
                    conn.commit()
                    logger.debug(f"清理过期数据库缓存 | count={len(expired_keys)}")
        except Exception as e:
            logger.error(f"清理过期缓存失败 | error={e}")
    
    # ==================== 基础操作 ====================
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                del self._cache[key]
                # 异步删除数据库记录
                threading.Thread(
                    target=self._delete_from_db, 
                    args=(key,), 
                    daemon=True
                ).start()
                logger.debug(f"缓存过期 | key={key}")
                return None
            
            logger.debug(f"缓存命中 | key={key} | remaining={entry.remaining_seconds()}s")
            return entry.data
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None, cache_type: str = "quote"):
        """设置缓存数据"""
        if ttl is None:
            ttl = self.DEFAULT_TTL.get(cache_type, 60)
        
        entry = CacheEntry(
            data=data,
            created_at=datetime.now(),
            ttl_seconds=ttl,
        )
        
        with self._lock:
            self._cache[key] = entry
        
        logger.debug(f"缓存写入 | key={key} | ttl={ttl}s")
        
        # 异步持久化到数据库
        threading.Thread(
            target=self._save_to_db, 
            args=(key, entry), 
            daemon=True
        ).start()
    
    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
        
        threading.Thread(
            target=self._delete_from_db, 
            args=(key,), 
            daemon=True
        ).start()
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
        
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()
            logger.info("缓存已清空")
        except Exception as e:
            logger.error(f"清空数据库缓存失败 | error={e}")
    
    def stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for e in self._cache.values() if e.is_expired())
        
        # 获取数据库统计
        try:
            with self._get_conn() as conn:
                db_count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        except:
            db_count = 0
        
        return {
            "memory_total": total,
            "memory_active": total - expired,
            "db_total": db_count,
        }
    
    def keys(self) -> list:
        """获取所有缓存 key"""
        with self._lock:
            return list(self._cache.keys())
    
    def cleanup_expired(self):
        """清理过期缓存"""
        # 清理内存
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
        
        # 清理数据库
        self._cleanup_expired_db()
        
        if expired_keys:
            logger.debug(f"清理过期缓存 | count={len(expired_keys)}")


# 全局缓存实例
market_cache = MarketCache()
