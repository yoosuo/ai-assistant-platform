# -*- coding: utf-8 -*-
"""
用户认证和权限管理模块
"""

import hashlib
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import request, session, jsonify, redirect, url_for
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    """用户认证管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_auth_tables()
    
    def init_auth_tables(self):
        """初始化认证相关数据表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    profile_data TEXT DEFAULT '{}'
                )
            ''')
            
            # 用户会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # IP黑名单表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT UNIQUE NOT NULL,
                    reason TEXT DEFAULT 'login_failures',
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    attempts_count INTEGER DEFAULT 0
                )
            ''')
            
            # 登录尝试记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    username TEXT,
                    success BOOLEAN NOT NULL,
                    attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT
                )
            ''')
            
            # 创建默认管理员账户（如果不存在）
            self._create_default_admin(cursor)
            
            conn.commit()
            logger.info("认证数据表初始化完成")
            
        except Exception as e:
            logger.error(f"初始化认证表失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _create_default_admin(self, cursor):
        """创建默认管理员账户"""
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            # 创建默认管理员
            salt = secrets.token_hex(32)
            password = "admin123"  # 默认密码，建议首次登录后修改
            password_hash = self._hash_password(password, salt)
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?)
            ''', ("admin", "admin@local.com", password_hash, salt, "admin"))
            
            logger.info("默认管理员账户已创建 - 用户名: admin, 密码: admin123")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """密码加盐哈希"""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _generate_session_token(self) -> str:
        """生成会话令牌"""
        return secrets.token_urlsafe(32)
    
    def register_user(self, username: str, email: str, password: str, role: str = 'user') -> Dict[str, Any]:
        """用户注册"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户名和邮箱是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                return {"success": False, "error": "用户名或邮箱已存在"}
            
            # 生成盐和密码哈希
            salt = secrets.token_hex(32)
            password_hash = self._hash_password(password, salt)
            
            # 插入新用户
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, salt, role))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"新用户注册成功: {username}")
            return {"success": True, "user_id": user_id, "message": "注册成功"}
            
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            conn.rollback()
            return {"success": False, "error": "注册失败，请稍后重试"}
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str, ip_address: str, user_agent: str = "") -> Dict[str, Any]:
        """用户登录认证"""
        # 检查IP是否被拉黑
        if self._is_ip_blacklisted(ip_address):
            self._log_login_attempt(ip_address, username, False, user_agent)
            return {"success": False, "error": "IP地址被暂时禁止登录，请24小时后重试"}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找用户
            cursor.execute('''
                SELECT id, username, email, password_hash, salt, role, is_active
                FROM users WHERE username = ? OR email = ?
            ''', (username, username))
            
            user = cursor.fetchone()
            
            if not user:
                self._log_login_attempt(ip_address, username, False, user_agent)
                self._check_and_blacklist_ip(ip_address)
                return {"success": False, "error": "用户名或密码错误"}
            
            user_id, db_username, email, password_hash, salt, role, is_active = user
            
            # 检查用户是否被禁用
            if not is_active:
                self._log_login_attempt(ip_address, username, False, user_agent)
                return {"success": False, "error": "账户已被禁用，请联系管理员"}
            
            # 验证密码
            if self._hash_password(password, salt) != password_hash:
                self._log_login_attempt(ip_address, username, False, user_agent)
                self._check_and_blacklist_ip(ip_address)
                return {"success": False, "error": "用户名或密码错误"}
            
            # 登录成功，创建会话
            session_token = self._generate_session_token()
            expires_at = datetime.now() + timedelta(days=30)  # 30天有效期
            
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, session_token, ip_address, user_agent, expires_at))
            
            # 更新最后登录时间
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            
            conn.commit()
            
            # 记录成功登录
            self._log_login_attempt(ip_address, username, True, user_agent)
            
            logger.info(f"用户登录成功: {db_username}")
            
            return {
                "success": True,
                "session_token": session_token,
                "user": {
                    "id": user_id,
                    "username": db_username,
                    "email": email,
                    "role": role
                },
                "message": "登录成功"
            }
            
        except Exception as e:
            logger.error(f"用户登录失败: {e}")
            conn.rollback()
            return {"success": False, "error": "登录失败，请稍后重试"}
        finally:
            conn.close()
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """验证会话有效性"""
        if not session_token:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT s.user_id, s.expires_at, u.username, u.email, u.role, u.is_active
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.is_active = 1
            ''', (session_token,))
            
            result = cursor.fetchone()
            
            if not result:
                return None
            
            user_id, expires_at, username, email, role, is_active = result
            
            # 检查会话是否过期
            expires_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expires_time < datetime.now():
                # 会话过期，设置为无效
                cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
                conn.commit()
                return None
            
            # 检查用户是否被禁用
            if not is_active:
                return None
            
            return {
                "user_id": user_id,
                "username": username,
                "email": email,
                "role": role
            }
            
        except Exception as e:
            logger.error(f"验证会话失败: {e}")
            return None
        finally:
            conn.close()
    
    def logout_user(self, session_token: str) -> bool:
        """用户退出登录"""
        if not session_token:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"用户退出失败: {e}")
            return False
        finally:
            conn.close()
    
    def _is_ip_blacklisted(self, ip_address: str) -> bool:
        """检查IP是否被拉黑"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT expires_at FROM ip_blacklist 
                WHERE ip_address = ? AND expires_at > CURRENT_TIMESTAMP
            ''', (ip_address,))
            
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"检查IP黑名单失败: {e}")
            return False
        finally:
            conn.close()
    
    def _log_login_attempt(self, ip_address: str, username: str, success: bool, user_agent: str = ""):
        """记录登录尝试"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO login_attempts (ip_address, username, success, user_agent)
                VALUES (?, ?, ?, ?)
            ''', (ip_address, username, success, user_agent))
            conn.commit()
        except Exception as e:
            logger.error(f"记录登录尝试失败: {e}")
        finally:
            conn.close()
    
    def _check_and_blacklist_ip(self, ip_address: str):
        """检查并拉黑IP（连续失败超过5次）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查最近1小时内的失败次数
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cursor.execute('''
                SELECT COUNT(*) FROM login_attempts 
                WHERE ip_address = ? AND success = 0 AND attempt_time > ?
            ''', (ip_address, one_hour_ago))
            
            failure_count = cursor.fetchone()[0]
            
            if failure_count >= 5:
                # 拉黑IP 24小时
                expires_at = datetime.now() + timedelta(hours=24)
                cursor.execute('''
                    INSERT OR REPLACE INTO ip_blacklist (ip_address, expires_at, attempts_count)
                    VALUES (?, ?, ?)
                ''', (ip_address, expires_at, failure_count))
                
                conn.commit()
                logger.warning(f"IP {ip_address} 已被拉黑24小时（失败次数: {failure_count}）")
        
        except Exception as e:
            logger.error(f"检查并拉黑IP失败: {e}")
        finally:
            conn.close()
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取用户当前密码信息
            cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return {"success": False, "error": "用户不存在"}
            
            password_hash, salt = result
            
            # 验证旧密码
            if self._hash_password(old_password, salt) != password_hash:
                return {"success": False, "error": "原密码错误"}
            
            # 生成新的盐和密码哈希
            new_salt = secrets.token_hex(32)
            new_password_hash = self._hash_password(new_password, new_salt)
            
            # 更新密码
            cursor.execute('''
                UPDATE users SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_password_hash, new_salt, user_id))
            
            conn.commit()
            
            logger.info(f"用户 {user_id} 密码修改成功")
            return {"success": True, "message": "密码修改成功"}
            
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            conn.rollback()
            return {"success": False, "error": "密码修改失败，请稍后重试"}
        finally:
            conn.close()


def require_auth(f):
    """装饰器：要求用户登录"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = session.get('session_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not session_token:
            if request.is_json:
                return jsonify({"success": False, "error": "需要登录"}), 401
            return redirect(url_for('login_page'))
        
        from config import Config
        auth_manager = AuthManager(Config.DATABASE_PATH)
        user_info = auth_manager.validate_session(session_token)
        
        if not user_info:
            if request.is_json:
                return jsonify({"success": False, "error": "会话已过期，请重新登录"}), 401
            session.pop('session_token', None)
            return redirect(url_for('login_page'))
        
        # 将用户信息添加到request对象
        request.current_user = user_info
        return f(*args, **kwargs)
    
    return decorated_function


def require_admin(f):
    """装饰器：要求管理员权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = session.get('session_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not session_token:
            if request.is_json:
                return jsonify({"success": False, "error": "需要登录"}), 401
            return redirect(url_for('login_page'))
        
        from config import Config
        auth_manager = AuthManager(Config.DATABASE_PATH)
        user_info = auth_manager.validate_session(session_token)
        
        if not user_info:
            if request.is_json:
                return jsonify({"success": False, "error": "会话已过期，请重新登录"}), 401
            session.pop('session_token', None)
            return redirect(url_for('login_page'))
        
        if user_info.get('role') != 'admin':
            if request.is_json:
                return jsonify({"success": False, "error": "需要管理员权限"}), 403
            return redirect(url_for('index'))
        
        request.current_user = user_info
        return f(*args, **kwargs)
    
    return decorated_function


def get_client_ip():
    """获取客户端IP地址"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr