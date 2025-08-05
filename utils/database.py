#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理 - SQLite操作封装
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        # 确保data目录存在
        self.data_dir = os.path.join(os.path.dirname(__file__), '../data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.db_path = os.path.join(self.data_dir, 'conversations.db')
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        
        # 用户会话表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER DEFAULT 1,
                assistant_type TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 会话消息表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        # 游戏会话表 - 重新设计
        conn.execute('''
            CREATE TABLE IF NOT EXISTS game_sessions (
                id TEXT PRIMARY KEY,
                game_type TEXT NOT NULL,
                user_id INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                current_phase TEXT DEFAULT 'init',
                phase_start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                game_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # AI角色表 - 每个游戏中的AI角色
        conn.execute('''
            CREATE TABLE IF NOT EXISTS game_characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                character_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                character_type TEXT NOT NULL,
                personality TEXT,
                background TEXT,
                secrets TEXT,
                memory TEXT,
                is_alive BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES game_sessions(id)
            )
        ''')
        
        # 游戏消息表 - 游戏内所有对话
        conn.execute('''
            CREATE TABLE IF NOT EXISTS game_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                speaker_id TEXT NOT NULL,
                speaker_name TEXT NOT NULL,
                speaker_type TEXT NOT NULL,
                message_type TEXT DEFAULT 'dialogue',
                content TEXT NOT NULL,
                phase TEXT,
                is_private BOOLEAN DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES game_sessions(id)
            )
        ''')
        
        # 游戏行动表 - 记录所有游戏行动
        conn.execute('''
            CREATE TABLE IF NOT EXISTS game_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_data TEXT,
                result TEXT,
                phase TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES game_sessions(id)
            )
        ''')
        
        # 游戏状态表 - 详细游戏状态
        conn.execute('''
            CREATE TABLE IF NOT EXISTS game_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                state_key TEXT NOT NULL,
                state_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES game_sessions(id),
                UNIQUE(session_id, state_key)
            )
        ''')
        
        # 游戏评分表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS game_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER DEFAULT 1,
                game_type TEXT NOT NULL,
                score INTEGER,
                performance_data TEXT,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES game_sessions(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ===== 会话管理 =====
    def create_conversation(self, session_id: str, user_id: int, assistant_type: str, title: str):
        """创建新会话"""
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO conversations (id, user_id, assistant_type, title) VALUES (?, ?, ?, ?)",
            (session_id, user_id, assistant_type, title)
        )
        conn.commit()
        conn.close()
    
    def get_conversation(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        conn = self.get_connection()
        cursor = conn.execute("SELECT * FROM conversations WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def rename_conversation(self, session_id: str, new_title: str) -> bool:
        """重命名会话"""
        conn = self.get_connection()
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_title, session_id)
        )
        changed = conn.total_changes > 0
        conn.commit()
        conn.close()
        return changed
    
    def delete_conversation(self, session_id: str) -> bool:
        """删除会话及其消息"""
        conn = self.get_connection()
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (session_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (session_id,))
        changed = conn.total_changes > 0
        conn.commit()
        conn.close()
        return changed
    
    def get_user_conversations(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取用户的会话列表"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit)
        )
        conversations = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return conversations
    
    def delete_conversation(self, session_id: str):
        """删除会话"""
        conn = self.get_connection()
        conn.execute("DELETE FROM conversations WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
    
    def delete_conversation_messages(self, session_id: str):
        """删除会话的所有消息"""
        conn = self.get_connection()
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (session_id,))
        conn.commit()
        conn.close()
    
    # ===== 游戏数据管理 =====
    
    def create_game_session(self, session_id: str, game_type: str, user_id: int = 1, config: Dict = None):
        """创建游戏会话"""
        conn = self.get_connection()
        config_json = json.dumps(config) if config else '{}'
        # 使用现有数据库结构中的game_state列
        conn.execute(
            "INSERT INTO game_sessions (id, game_type, user_id, game_state) VALUES (?, ?, ?, ?)",
            (session_id, game_type, user_id, config_json)
        )
        conn.commit()
        conn.close()
    
    def update_game_phase(self, session_id: str, phase: str):
        """更新游戏阶段 - 临时禁用，因为数据库结构不匹配"""
        # 现有数据库没有current_phase列，暂时跳过
        # TODO: 将来更新数据库结构后启用
        pass
    
    def get_game_session(self, session_id: str) -> Optional[Dict]:
        """获取游戏会话信息"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM game_sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def add_game_character(self, session_id: str, character_id: str, name: str, 
                          character_type: str, personality: str = "", background: str = "", 
                          secrets: str = "", memory: str = ""):
        """添加游戏角色"""
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO game_characters (session_id, character_id, character_name, character_type, personality, background, secrets, memory) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, character_id, name, character_type, personality, background, secrets, memory)
        )
        conn.commit()
        conn.close()
    
    def update_character_memory(self, session_id: str, character_id: str, memory: str):
        """更新角色记忆"""
        conn = self.get_connection()
        conn.execute(
            "UPDATE game_characters SET memory = ? WHERE session_id = ? AND character_id = ?",
            (memory, session_id, character_id)
        )
        conn.commit()
        conn.close()
    
    def get_game_characters(self, session_id: str) -> List[Dict]:
        """获取游戏角色列表"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM game_characters WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        )
        characters = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return characters
    
    def add_game_message(self, session_id: str, speaker_id: str, speaker_name: str, 
                        speaker_type: str, content: str, message_type: str = 'dialogue',
                        phase: str = '', is_private: bool = False):
        """添加游戏消息"""
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO game_messages (session_id, speaker_id, speaker_name, speaker_type, message_type, content, phase, is_private) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, speaker_id, speaker_name, speaker_type, message_type, content, phase, int(is_private))
        )
        conn.commit()
        conn.close()
    
    def get_game_messages(self, session_id: str, phase: str = None, limit: int = 50) -> List[Dict]:
        """获取游戏消息"""
        conn = self.get_connection()
        if phase:
            cursor = conn.execute(
                "SELECT * FROM game_messages WHERE session_id = ? AND phase = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, phase, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM game_messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                (session_id, limit)
            )
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return list(reversed(messages))  # 返回正序
    
    def add_game_action(self, session_id: str, actor_id: str, action_type: str, 
                       action_data: Dict = None, result: str = "", phase: str = ""):
        """添加游戏行动"""
        conn = self.get_connection()
        action_json = json.dumps(action_data) if action_data else '{}'
        conn.execute(
            "INSERT INTO game_actions (session_id, actor_id, action_type, action_data, result, phase) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, actor_id, action_type, action_json, result, phase)
        )
        conn.commit()
        conn.close()
    
    def get_game_actions(self, session_id: str, phase: str = None) -> List[Dict]:
        """获取游戏行动"""
        conn = self.get_connection()
        if phase:
            cursor = conn.execute(
                "SELECT * FROM game_actions WHERE session_id = ? AND phase = ? ORDER BY timestamp",
                (session_id, phase)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM game_actions WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
        actions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return actions
    
    def set_game_state(self, session_id: str, key: str, value: str):
        """设置游戏状态"""
        conn = self.get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO game_states (session_id, state_key, state_value) VALUES (?, ?, ?)",
            (session_id, key, value)
        )
        conn.commit()
        conn.close()
    
    def get_game_state_value(self, session_id: str, key: str) -> str:
        """获取特定游戏状态值"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT state_value FROM game_states WHERE session_id = ? AND state_key = ?",
            (session_id, key)
        )
        row = cursor.fetchone()
        conn.close()
        return row['state_value'] if row else None
    
    def get_all_game_states(self, session_id: str) -> Dict:
        """获取所有游戏状态"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT state_key, state_value FROM game_states WHERE session_id = ?",
            (session_id,)
        )
        states = {row['state_key']: row['state_value'] for row in cursor.fetchall()}
        conn.close()
        return states
    
    def save_game_score(self, session_id: str, user_id: int, game_type: str, 
                       score: int, performance_data: Dict = None):
        """保存游戏评分"""
        conn = self.get_connection()
        performance_json = json.dumps(performance_data) if performance_data else '{}'
        conn.execute(
            "INSERT INTO game_scores (session_id, user_id, game_type, score, performance_data) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, game_type, score, performance_json)
        )
        conn.commit()
        conn.close()
    
    # ===== 消息管理 =====
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Dict = None):
        """添加消息"""
        conn = self.get_connection()
        metadata_str = json.dumps(metadata) if metadata else None
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, metadata) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, metadata_str)
        )
        # 更新会话的最后更新时间
        conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,)
        )
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict]:
        """获取会话历史"""
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC LIMIT ?",
            (conversation_id, limit)
        )
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg['metadata']:
                msg['metadata'] = json.loads(msg['metadata'])
            messages.append(msg)
        conn.close()
        return messages
    
    # ===== 游戏会话管理 =====
    def save_game_session(self, session_id: str, game_type: str, game_state: Dict, user_id: int = 1):
        """保存游戏会话"""
        conn = self.get_connection()
        game_state_str = json.dumps(game_state, ensure_ascii=False)
        
        # 使用REPLACE实现插入或更新
        conn.execute('''
            INSERT OR REPLACE INTO game_sessions 
            (id, game_type, user_id, game_state, updated_at) 
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (session_id, game_type, user_id, game_state_str))
        
        conn.commit()
        conn.close()
    
    def get_game_state(self, session_id: str) -> Optional[Dict]:
        """获取游戏状态"""
        conn = self.get_connection()
        cursor = conn.execute("SELECT game_state FROM game_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row['game_state'])
        return None
    
    def update_game_state(self, session_id: str, game_state: Dict):
        """更新游戏状态"""
        conn = self.get_connection()
        game_state_str = json.dumps(game_state, ensure_ascii=False)
        conn.execute(
            "UPDATE game_sessions SET game_state = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (game_state_str, session_id)
        )
        conn.commit()
        conn.close()
    
    def get_user_game_sessions(self, user_id: int, game_type: str = None) -> List[Dict]:
        """获取用户的游戏会话列表"""
        conn = self.get_connection()
        
        if game_type:
            cursor = conn.execute(
                "SELECT * FROM game_sessions WHERE user_id = ? AND game_type = ? ORDER BY updated_at DESC",
                (user_id, game_type)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM game_sessions WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
        
        sessions = []
        for row in cursor.fetchall():
            session = dict(row)
            session['game_state'] = json.loads(session['game_state'])
            sessions.append(session)
        
        conn.close()
        return sessions