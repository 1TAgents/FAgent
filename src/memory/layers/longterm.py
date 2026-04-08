"""
L3 长期记忆

永久记忆，SQLite + 向量存储
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class LongTermMemory:
    """
    L3 长期记忆 - 永久存储，SQLite
    
    存储:
    - 用户画像和偏好
    - 交易历史
    - 策略库
    - 知识库
    - 合规日志
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite 数据库
        self.profile_db = self.data_dir / "longterm" / "profile.db"
        self.trades_db = self.data_dir / "longterm" / "trades.db"
        
        self._init_databases()
    
    def _init_databases(self):
        """初始化数据库"""
        # 用户画像表
        conn = sqlite3.connect(self.profile_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                risk_tolerance TEXT NOT NULL,
                preferred_holding_period TEXT NOT NULL,
                max_position_ratio REAL NOT NULL,
                stop_loss_ratio REAL NOT NULL,
                take_profit_ratio REAL NOT NULL,
                preferred_industries TEXT,
                trading_hours TEXT NOT NULL,
                notification_preference TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        
        # 交易记录表
        conn = sqlite3.connect(self.trades_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                executed_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                strategy_id TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_executed_at ON trades(executed_at)')
        conn.commit()
        conn.close()
    
    # ==================== 用户画像 ====================
    
    def get_profile(self, user_id: str = "default") -> Optional[Dict]:
        """获取用户画像"""
        conn = sqlite3.connect(self.profile_db)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "user_id": row[0],
                "risk_tolerance": row[1],
                "preferred_holding_period": row[2],
                "max_position_ratio": row[3],
                "stop_loss_ratio": row[4],
                "take_profit_ratio": row[5],
                "preferred_industries": json.loads(row[6]) if row[6] else [],
                "trading_hours": row[7],
                "notification_preference": row[8],
                "created_at": row[9],
                "updated_at": row[10]
            }
        return None
    
    def update_profile(self, profile: Dict):
        """更新用户画像"""
        conn = sqlite3.connect(self.profile_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.get("user_id", "default"),
            profile.get("risk_tolerance", "medium"),
            profile.get("preferred_holding_period", "medium"),
            profile.get("max_position_ratio", 0.3),
            profile.get("stop_loss_ratio", 0.05),
            profile.get("take_profit_ratio", 0.2),
            json.dumps(profile.get("preferred_industries", [])),
            profile.get("trading_hours", "market_hours"),
            profile.get("notification_preference", "important_only"),
            profile.get("created_at", datetime.now().isoformat()),
            profile.get("updated_at", datetime.now().isoformat())
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== 交易记录 ====================
    
    def record_trade(self, trade: Dict):
        """记录交易"""
        conn = sqlite3.connect(self.trades_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade["trade_id"], trade["symbol"], trade["trade_type"],
            trade["quantity"], trade["price"], trade["amount"],
            trade["executed_at"], trade["reason"],
            trade.get("strategy_id"), trade.get("notes"),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """获取交易记录"""
        conn = sqlite3.connect(self.trades_db)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT * FROM trades WHERE symbol = ? 
                ORDER BY executed_at DESC LIMIT ?
            ''', (symbol, limit))
        else:
            cursor.execute('''
                SELECT * FROM trades ORDER BY executed_at DESC LIMIT ?
            ''', (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                "trade_id": row[0], "symbol": row[1], "trade_type": row[2],
                "quantity": row[3], "price": row[4], "amount": row[5],
                "executed_at": row[6], "reason": row[7], "strategy_id": row[8],
                "notes": row[9]
            })
        
        conn.close()
        return trades
