"""
AuthManager - 用户认证和权限管理模块
版本: 3.0 (PySide6版本)
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Callable, Tuple, List
from functools import wraps
import traceback

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

from .database_manager import DatabaseManager
from .time_utils import get_local_time_str


class AuthManager:
    """用户认证管理器"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.current_user: Optional[Dict] = None
        self.session_timeout = timedelta(hours=8)
        self._init_default_users()

    def _init_default_users(self):
        """初始化默认用户账号"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                if cursor.fetchone()[0] == 0:
                    print("[INFO] 创建默认用户账号...")

                    # 开发者账号
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, full_name, role, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ("developer", self._hash_password("125222"), "系统开发者", "developer", get_local_time_str(), get_local_time_str()))

                    # 管理员账号
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, full_name, role, created_by, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ("admin", self._hash_password("admin123"), "管理员", "admin", 1, get_local_time_str(), get_local_time_str()))

                    # 普通用户
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, full_name, role, created_by, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ("operator01", self._hash_password("123456"), "操作员01", "user", 2, get_local_time_str(), get_local_time_str()))

                    conn.commit()
                    print("[INFO] 默认用户创建成功")
        except Exception as e:
            print(f"[ERROR] 初始化默认用户失败: {e}")

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == password_hash

    def login(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """用户登录"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()

                if not row:
                    return False, "用户名或密码错误"

                user = dict(row)
                if not user['is_active']:
                    return False, "账号已被禁用"

                if not self._verify_password(password, user['password_hash']):
                    return False, "用户名或密码错误"

                self.current_user = user
                cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (get_local_time_str(), user['id']))
                conn.commit()
                self._log_operation(user['id'], username, "用户登录", "user", user['id'])
                return True, None
        except Exception as e:
            print(f"[ERROR] 登录失败: {e}")
            return False, f"登录失败: {str(e)}"

    def verify_credentials(self, username: str, password: str) -> bool:
        """验证用户凭据"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password_hash, is_active FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    return False
                return row['is_active'] and self._verify_password(password, row['password_hash'])
        except Exception as e:
            print(f"[ERROR] 验证凭据失败: {e}")
            return False

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """根据用户名查询用户信息"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[ERROR] 查询用户失败: {e}")
            return None

    def logout(self):
        """登出"""
        if self.current_user:
            try:
                self._log_operation(self.current_user['id'], self.current_user['username'], "用户登出", "user", self.current_user['id'])
            except Exception:
                pass
        self.current_user = None

    def is_authenticated(self) -> bool:
        return self.current_user is not None

    def get_current_user(self) -> Optional[Dict]:
        return self.current_user

    def get_current_user_id(self) -> Optional[int]:
        return self.current_user['id'] if self.current_user else None

    def get_current_username(self) -> Optional[str]:
        return self.current_user['username'] if self.current_user else None

    def get_current_role(self) -> Optional[str]:
        return self.current_user['role'] if self.current_user else None

    def has_permission(self, required_role: str) -> bool:
        """检查当前用户是否有指定权限"""
        if not self.current_user:
            return False
        role_hierarchy = {'user': 1, 'admin': 2, 'developer': 3}
        return role_hierarchy.get(self.current_user['role'], 0) >= role_hierarchy.get(required_role, 999)

    def require_permission(self, required_role: str):
        """权限检查装饰器"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.has_permission(required_role):
                    raise PermissionError(f"需要 {required_role} 权限")
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """修改密码"""
        try:
            if len(new_password) < 6:
                return False, "密码长度至少6位"

            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    return False, "用户不存在"

                user = dict(row)
                if not self._verify_password(old_password, user['password_hash']):
                    return False, "旧密码错误"

                cursor.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                               (self._hash_password(new_password), get_local_time_str(), user['id']))
                conn.commit()
                self._log_operation(user['id'], username, "修改密码", "user", user['id'])
                return True, None
        except Exception as e:
            return False, f"修改密码失败: {str(e)}"

    def reset_password(self, username: str, new_password: str, operator_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """重置密码（管理员功能）"""
        try:
            if not self.has_permission('admin'):
                return False, "需要管理员权限"
            if len(new_password) < 6:
                return False, "密码长度至少6位"

            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    return False, "用户不存在"

                user = dict(row)
                if user['role'] == 'developer' and self.current_user['role'] != 'developer':
                    return False, "无权重置开发者密码"

                cursor.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                               (self._hash_password(new_password), get_local_time_str(), user['id']))
                conn.commit()
                return True, None
        except Exception as e:
            return False, f"重置密码失败: {str(e)}"

    def get_all_users(self, active_only: bool = False) -> List[Dict]:
        """获取所有用户列表"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                sql = "SELECT id, username, full_name, role, is_active, created_at, updated_at, last_login FROM users"
                if active_only:
                    sql += " WHERE is_active = 1"
                sql += " ORDER BY role, username"
                cursor.execute(sql)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 获取用户列表失败: {e}")
            return []

    def add_user(self, username: str, password: str, full_name: str, role: str = 'user') -> Tuple[bool, Optional[str], Optional[int]]:
        """添加新用户"""
        try:
            if not self.has_permission('admin'):
                return False, "需要管理员权限", None
            if role not in ['developer', 'admin', 'user']:
                return False, f"无效的角色: {role}", None
            if role == 'developer' and self.current_user['role'] != 'developer':
                return False, "只有开发者可以创建开发者账号", None
            if len(password) < 6:
                return False, "密码长度至少6位", None

            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                if cursor.fetchone():
                    return False, "用户名已存在", None

                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, role, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (username, self._hash_password(password), full_name, role, self.current_user['id'], get_local_time_str(), get_local_time_str()))
                conn.commit()
                return True, None, cursor.lastrowid
        except Exception as e:
            return False, f"创建用户失败: {str(e)}", None

    def update_user(self, user_id: int, full_name: Optional[str] = None, role: Optional[str] = None, is_active: Optional[bool] = None) -> Tuple[bool, Optional[str]]:
        """更新用户信息"""
        try:
            if not self.has_permission('admin'):
                return False, "需要管理员权限"

            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    return False, "用户不存在"

                target_user = dict(row)
                if target_user['role'] == 'developer' and self.current_user['role'] != 'developer':
                    return False, "无权修改开发者账号"

                updates, params = [], []
                if full_name is not None:
                    updates.append("full_name = ?")
                    params.append(full_name)
                if role is not None:
                    if role not in ['developer', 'admin', 'user']:
                        return False, f"无效的角色: {role}"
                    if role == 'developer' and self.current_user['role'] != 'developer':
                        return False, "只有开发者可以设置开发者角色"
                    updates.append("role = ?")
                    params.append(role)
                if is_active is not None:
                    if user_id == self.current_user['id'] and not is_active:
                        return False, "不能禁用自己的账号"
                    updates.append("is_active = ?")
                    params.append(1 if is_active else 0)

                if not updates:
                    return False, "没有要更新的字段"

                updates.append("updated_at = ?")
                params.append(get_local_time_str())
                params.append(user_id)

                cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return True, None
        except Exception as e:
            return False, f"更新用户失败: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """删除用户（软删除）"""
        try:
            if not self.has_permission('admin'):
                return False, "需要管理员权限"
            if user_id == self.current_user['id']:
                return False, "不能删除自己的账号"

            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    return False, "用户不存在"

                user = dict(row)
                if user['role'] == 'developer' and self.current_user['role'] != 'developer':
                    return False, "无权删除开发者账号"

                cursor.execute("UPDATE users SET is_active = 0, updated_at = ? WHERE id = ?", (get_local_time_str(), user_id))
                conn.commit()
                return True, None
        except Exception as e:
            return False, f"删除用户失败: {str(e)}"

    def activate_user(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """激活用户"""
        return self.update_user(user_id, is_active=True)

    def _log_operation(self, user_id: int, username: str, action: str, target_type: str, target_id: int, details: Optional[str] = None):
        """记录操作日志"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO operation_logs (user_id, username, action, target_type, target_id, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, username, action, target_type, target_id, details, get_local_time_str()))
                conn.commit()
        except Exception:
            pass

    def log_operation(self, action: str, target_type: str, target_id: int, details: Optional[str] = None):
        """记录当前用户的操作日志"""
        if self.current_user:
            self._log_operation(self.current_user['id'], self.current_user['username'], action, target_type, target_id, details)


# 全局单例
auth_manager = AuthManager()
