# -*- coding: utf-8 -*-
"""
用户管理服务模块
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils.auth import AuthManager

logger = logging.getLogger(__name__)

class UserService:
    """用户管理服务"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.auth_manager = AuthManager(db_path)
    
    def get_all_users(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取所有用户列表（分页）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取总数
            cursor.execute("SELECT COUNT(*) FROM users")
            total_count = cursor.fetchone()[0]
            
            # 获取分页数据
            offset = (page - 1) * page_size
            cursor.execute('''
                SELECT id, username, email, role, is_active, created_at, last_login
                FROM users 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
            
            users = []
            for row in cursor.fetchall():
                user_id, username, email, role, is_active, created_at, last_login = row
                users.append({
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "role": role,
                    "is_active": bool(is_active),
                    "created_at": created_at,
                    "last_login": last_login,
                    "status": "正常" if is_active else "已禁用"
                })
            
            total_pages = (total_count + page_size - 1) // page_size
            
            return {
                "success": True,
                "users": users,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_prev": page > 1,
                    "has_next": page < total_pages
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return {"success": False, "error": "获取用户列表失败"}
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取用户基本信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, role, is_active, created_at, last_login
                FROM users 
                WHERE id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            user_id, username, email, role, is_active, created_at, last_login = row
            return {
                "id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "is_active": bool(is_active),
                "created_at": created_at,
                "last_login": last_login
            }
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_user_detail(self, user_id: int) -> Dict[str, Any]:
        """获取用户详细信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, role, is_active, created_at, updated_at, 
                       last_login, profile_data
                FROM users WHERE id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return {"success": False, "error": "用户不存在"}
            
            user_id, username, email, role, is_active, created_at, updated_at, last_login, profile_data = result
            
            # 获取用户的会话信息
            cursor.execute('''
                SELECT COUNT(*) FROM user_sessions 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            active_sessions = cursor.fetchone()[0]
            
            # 获取用户的登录记录（最近10次）
            cursor.execute('''
                SELECT attempt_time, success, ip_address
                FROM login_attempts 
                WHERE username = ? 
                ORDER BY attempt_time DESC 
                LIMIT 10
            ''', (username,))
            
            login_history = []
            for attempt_time, success, ip_address in cursor.fetchall():
                login_history.append({
                    "time": attempt_time,
                    "success": bool(success),
                    "ip_address": ip_address,
                    "status": "成功" if success else "失败"
                })
            
            try:
                profile = json.loads(profile_data) if profile_data else {}
            except:
                profile = {}
            
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "role": role,
                    "is_active": bool(is_active),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "last_login": last_login,
                    "profile": profile,
                    "active_sessions": active_sessions,
                    "login_history": login_history
                }
            }
            
        except Exception as e:
            logger.error(f"获取用户详情失败: {e}")
            return {"success": False, "error": "获取用户详情失败"}
        finally:
            conn.close()
    
    def update_user(self, user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否存在
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                return {"success": False, "error": "用户不存在"}
            
            # 构建更新SQL
            update_fields = []
            update_values = []
            
            allowed_fields = ['username', 'email', 'role', 'is_active', 'profile_data']
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == 'profile_data' and isinstance(value, dict):
                        value = json.dumps(value)
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return {"success": False, "error": "没有可更新的字段"}
            
            # 检查用户名和邮箱唯一性
            if 'username' in updates:
                cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (updates['username'], user_id))
                if cursor.fetchone():
                    return {"success": False, "error": "用户名已存在"}
            
            if 'email' in updates:
                cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (updates['email'], user_id))
                if cursor.fetchone():
                    return {"success": False, "error": "邮箱已存在"}
            
            # 执行更新
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(user_id)
            
            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, update_values)
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"用户 {user_id} 信息更新成功")
                return {"success": True, "message": "用户信息更新成功"}
            else:
                return {"success": False, "error": "更新失败"}
                
        except Exception as e:
            logger.error(f"更新用户信息失败: {e}")
            conn.rollback()
            return {"success": False, "error": "更新用户信息失败"}
        finally:
            conn.close()
    
    def reset_user_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """重置用户密码（管理员功能）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查用户是否存在
            cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if not result:
                return {"success": False, "error": "用户不存在"}
            
            username = result[0]
            
            # 生成新的盐和密码哈希
            import secrets
            salt = secrets.token_hex(32)
            password_hash = self.auth_manager._hash_password(new_password, salt)
            
            # 更新密码
            cursor.execute('''
                UPDATE users SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (password_hash, salt, user_id))
            
            # 清除该用户的所有活跃会话
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            conn.commit()
            
            logger.info(f"管理员重置用户 {username} 的密码")
            return {"success": True, "message": "密码重置成功，用户需要重新登录"}
            
        except Exception as e:
            logger.error(f"重置用户密码失败: {e}")
            conn.rollback()
            return {"success": False, "error": "重置密码失败"}
        finally:
            conn.close()
    
    def toggle_user_status(self, user_id: int) -> Dict[str, Any]:
        """切换用户状态（启用/禁用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取当前状态
            cursor.execute("SELECT username, is_active FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if not result:
                return {"success": False, "error": "用户不存在"}
            
            username, is_active = result
            new_status = not bool(is_active)
            
            # 更新状态
            cursor.execute('''
                UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_status, user_id))
            
            # 如果禁用用户，清除其活跃会话
            if not new_status:
                cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            conn.commit()
            
            status_text = "启用" if new_status else "禁用"
            logger.info(f"用户 {username} 已被{status_text}")
            
            return {
                "success": True, 
                "message": f"用户已{status_text}",
                "is_active": new_status
            }
            
        except Exception as e:
            logger.error(f"切换用户状态失败: {e}")
            conn.rollback()
            return {"success": False, "error": "操作失败"}
        finally:
            conn.close()
    
    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """删除用户（软删除 - 禁用账户）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否为管理员
            cursor.execute("SELECT username, role FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if not result:
                return {"success": False, "error": "用户不存在"}
            
            username, role = result
            
            # 防止删除最后一个管理员
            if role == 'admin':
                cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1")
                admin_count = cursor.fetchone()[0]
                if admin_count <= 1:
                    return {"success": False, "error": "无法删除最后一个管理员账户"}
            
            # 禁用用户（软删除）
            cursor.execute('''
                UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user_id,))
            
            # 清除用户会话
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            conn.commit()
            
            logger.info(f"用户 {username} 已被删除（禁用）")
            return {"success": True, "message": "用户已删除"}
            
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            conn.rollback()
            return {"success": False, "error": "删除用户失败"}
        finally:
            conn.close()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 用户统计
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            stats['active_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            stats['admin_users'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 0")
            stats['disabled_users'] = cursor.fetchone()[0]
            
            # 会话统计
            cursor.execute("SELECT COUNT(*) FROM user_sessions WHERE is_active = 1")
            stats['active_sessions'] = cursor.fetchone()[0]
            
            # 今日登录统计
            cursor.execute('''
                SELECT COUNT(*) FROM login_attempts 
                WHERE DATE(attempt_time) = DATE('now') AND success = 1
            ''')
            stats['today_logins'] = cursor.fetchone()[0]
            
            # IP黑名单统计
            cursor.execute('''
                SELECT COUNT(*) FROM ip_blacklist 
                WHERE expires_at > CURRENT_TIMESTAMP
            ''')
            stats['blocked_ips'] = cursor.fetchone()[0]
            
            # 最近注册用户
            cursor.execute('''
                SELECT username, created_at FROM users 
                ORDER BY created_at DESC LIMIT 5
            ''')
            stats['recent_users'] = [
                {"username": username, "created_at": created_at}
                for username, created_at in cursor.fetchall()
            ]
            
            return {"success": True, "stats": stats}
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {"success": False, "error": "获取统计信息失败"}
        finally:
            conn.close()
    
    def get_login_logs(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """获取登录日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取总数
            cursor.execute("SELECT COUNT(*) FROM login_attempts")
            total_count = cursor.fetchone()[0]
            
            # 获取分页数据
            offset = (page - 1) * page_size
            cursor.execute('''
                SELECT username, ip_address, success, attempt_time, user_agent
                FROM login_attempts 
                ORDER BY attempt_time DESC
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
            
            logs = []
            for username, ip_address, success, attempt_time, user_agent in cursor.fetchall():
                logs.append({
                    "username": username,
                    "ip_address": ip_address,
                    "success": bool(success),
                    "attempt_time": attempt_time,
                    "user_agent": user_agent,
                    "status": "成功" if success else "失败"
                })
            
            total_pages = (total_count + page_size - 1) // page_size
            
            return {
                "success": True,
                "logs": logs,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_prev": page > 1,
                    "has_next": page < total_pages
                }
            }
            
        except Exception as e:
            logger.error(f"获取登录日志失败: {e}")
            return {"success": False, "error": "获取登录日志失败"}
        finally:
            conn.close()
    
    def clear_expired_sessions(self) -> int:
        """清理过期会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE user_sessions SET is_active = 0 
                WHERE expires_at < CURRENT_TIMESTAMP AND is_active = 1
            ''')
            cleared_count = cursor.rowcount
            conn.commit()
            
            if cleared_count > 0:
                logger.info(f"清理了 {cleared_count} 个过期会话")
            
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0
        finally:
            conn.close()
    
    def clear_expired_blacklist(self) -> int:
        """清理过期的IP黑名单"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM ip_blacklist WHERE expires_at < CURRENT_TIMESTAMP')
            cleared_count = cursor.rowcount
            conn.commit()
            
            if cleared_count > 0:
                logger.info(f"清理了 {cleared_count} 个过期IP黑名单记录")
            
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理过期黑名单失败: {e}")
            return 0
        finally:
            conn.close()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户统计数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取用户基本信息
            cursor.execute('''
                SELECT username, email, created_at, last_login
                FROM users 
                WHERE id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if not user_data:
                return {}
            
            username, email, created_at, last_login = user_data
            
            # 计算使用天数
            try:
                if isinstance(created_at, str):
                    created_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                else:
                    created_date = created_at
                days_since_created = (datetime.now() - created_date).days
            except:
                days_since_created = 0
            
            # 获取对话统计（假设有conversations表）
            try:
                cursor.execute('''
                    SELECT COUNT(*) FROM conversations 
                    WHERE session_id IN (
                        SELECT DISTINCT session_id FROM messages 
                        WHERE role = 'user'
                    )
                ''')
                total_conversations = cursor.fetchone()[0] or 0
            except:
                total_conversations = 0
                
            # 获取消息统计
            try:
                cursor.execute('''
                    SELECT COUNT(*) FROM messages 
                    WHERE role = 'user'
                ''')
                total_messages = cursor.fetchone()[0] or 0
            except:
                total_messages = 0
            
            # 获取登录次数统计
            try:
                cursor.execute('''
                    SELECT COUNT(*) FROM login_logs 
                    WHERE username = ? AND status = 'success'
                ''', (username,))
                login_count = cursor.fetchone()[0] or 0
            except:
                login_count = 1  # 至少当前这次登录
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "days_since_created": days_since_created,
                "login_count": login_count,
                "last_login": last_login or "从未登录"
            }
            
        except Exception as e:
            logger.error(f"获取用户统计数据失败: {e}")
            return {
                "total_conversations": 0,
                "total_messages": 0,
                "days_since_created": 0,
                "login_count": 0,
                "last_login": "未知"
            }
        finally:
            cursor.close()
            conn.close()