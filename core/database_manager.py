"""
DatabaseManager - 数据库核心管理模块
负责所有数据库操作，提供统一的数据访问接口
版本: 3.0 (PySide6版本)
"""

import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from contextlib import contextmanager
import traceback

from .time_utils import get_local_time_str


class DatabaseManager:
    """数据库管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, production_db: str = "production.db", system_db: str = "system.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, production_db: str = "production.db", system_db: str = "system.db"):
        # 避免重复初始化
        if hasattr(self, '_initialized'):
            return

        # 创建 data 文件夹
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # 双数据库架构（存放在 data 文件夹）
        self.production_db = str(data_dir / production_db)  # 生产数据库
        self.system_db = str(data_dir / system_db)          # 系统数据库
        self._local = threading.local()
        self._initialized = True

        # UI窗口引用（用于显示重连对话框）
        self.root_window = None

        # 全局重连状态管理（防止并发重连）
        self._reconnecting = False
        self._reconnect_lock = threading.Lock()
        self._reconnect_event = threading.Event()
        self._reconnect_success = False

        # 初始化数据库
        self.initialize_database()

    @contextmanager
    def get_connection(self, db_type: str = 'production'):
        """获取线程本地数据库连接（上下文管理器）

        Args:
            db_type: 'production' 或 'system'
        """
        conn_attr = f'conn_{db_type}'
        db_path = self.production_db if db_type == 'production' else self.system_db

        if not hasattr(self._local, conn_attr):
            conn = sqlite3.connect(
                db_path,
                check_same_thread=False,
                timeout=30.0
            )
            conn.row_factory = sqlite3.Row

            # 尝试启用WAL模式
            try:
                result = conn.execute("PRAGMA journal_mode=WAL").fetchone()
                if result and result[0].upper() != 'WAL':
                    print(f"[WARNING] WAL模式启用失败，当前模式: {result[0]}")
            except sqlite3.OperationalError as e:
                print(f"[WARNING] 无法启用WAL模式（{e}），降级到DELETE模式")
                try:
                    conn.execute("PRAGMA journal_mode=DELETE")
                except Exception:
                    pass

            conn.execute("PRAGMA busy_timeout=30000")
            setattr(self._local, conn_attr, conn)

        conn = getattr(self._local, conn_attr)

        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e

    def initialize_database(self):
        """初始化双数据库（执行SQL脚本）"""
        try:
            # 初始化生产数据库
            prod_sql_file = Path(__file__).parent / "production_init.sql"
            if not prod_sql_file.exists():
                raise FileNotFoundError(f"生产数据库脚本不存在: {prod_sql_file}")

            with open(prod_sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            with self.get_connection('production') as conn:
                conn.executescript(sql_script)
                conn.commit()
            print(f"[INFO] 生产数据库初始化成功: {self.production_db}")

            # 初始化系统数据库
            sys_sql_file = Path(__file__).parent / "system_init.sql"
            if not sys_sql_file.exists():
                raise FileNotFoundError(f"系统数据库脚本不存在: {sys_sql_file}")

            with open(sys_sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            with self.get_connection('system') as conn:
                conn.executescript(sql_script)
                conn.commit()
            print(f"[INFO] 系统数据库初始化成功: {self.system_db}")

            # 自动迁移数据库schema
            self._migrate_database_schema()

        except Exception as e:
            print(f"[ERROR] 数据库初始化失败: {e}")
            traceback.print_exc()
            raise

    def _migrate_database_schema(self):
        """迁移数据库schema - 添加新字段"""
        try:
            with self.get_connection('production') as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(barcodes)")
                columns = [col[1] for col in cursor.fetchall()]

                if 'is_printed' not in columns:
                    print("[INFO] 数据库迁移: 添加barcodes.is_printed字段...")
                    cursor.execute("ALTER TABLE barcodes ADD COLUMN is_printed BOOLEAN DEFAULT 0")
                    conn.commit()

                if 'last_print_time' not in columns:
                    print("[INFO] 数据库迁移: 添加barcodes.last_print_time字段...")
                    cursor.execute("ALTER TABLE barcodes ADD COLUMN last_print_time DATETIME")
                    conn.commit()

            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='operation_logs'")
                if not cursor.fetchone():
                    print("[INFO] 数据库迁移: 创建operation_logs表...")
                    cursor.execute("""
                        CREATE TABLE operation_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            username VARCHAR(50),
                            action VARCHAR(50) NOT NULL,
                            target_type VARCHAR(50),
                            target_id INTEGER,
                            details TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id)
                        )
                    """)
                    cursor.execute("CREATE INDEX idx_operation_logs_user ON operation_logs(user_id)")
                    cursor.execute("CREATE INDEX idx_operation_logs_action ON operation_logs(action)")
                    cursor.execute("CREATE INDEX idx_operation_logs_time ON operation_logs(created_at)")
                    conn.commit()

                # 迁移：创建 print_recipes 表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='print_recipes'")
                if not cursor.fetchone():
                    print("[INFO] 数据库迁移: 创建print_recipes表...")
                    cursor.execute("""
                        CREATE TABLE print_recipes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            recipe_name VARCHAR(50) NOT NULL UNIQUE,
                            barcode_type VARCHAR(20) DEFAULT 'CODE39',
                            label_width REAL DEFAULT 70.0,
                            label_height REAL DEFAULT 20.0,
                            barcode_width REAL DEFAULT 0.25,
                            barcode_height REAL DEFAULT 10.0,
                            barcode_top_margin REAL DEFAULT 2.0,
                            font_size INTEGER DEFAULT 12,
                            text_gap REAL DEFAULT -1.0,
                            auto_print_repeat_count INTEGER DEFAULT 1,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cursor.execute("CREATE INDEX idx_print_recipes_name ON print_recipes(recipe_name)")
                    # 插入默认配方
                    cursor.execute("""
                        INSERT INTO print_recipes (id, recipe_name, barcode_type, label_width, label_height,
                            barcode_width, barcode_height, barcode_top_margin, font_size, text_gap, auto_print_repeat_count)
                        VALUES (1, '默认配方', 'CODE39', 70.0, 20.0, 0.25, 10.0, 2.0, 12, -1.0, 1)
                    """)
                    # 添加当前配方ID配置
                    cursor.execute("""
                        INSERT OR IGNORE INTO ui_settings (key, value, category, data_type, description)
                        VALUES ('print_current_recipe_id', '1', 'print', 'int', '当前使用的打印配方ID')
                    """)
                    conn.commit()
                    print("[INFO] print_recipes表创建成功，已插入默认配方")

        except Exception as e:
            print(f"[WARN] 数据库schema迁移失败: {e}")

    def close_all(self):
        """关闭所有连接"""
        for db_type in ['production', 'system']:
            conn_attr = f'conn_{db_type}'
            if hasattr(self._local, conn_attr):
                try:
                    getattr(self._local, conn_attr).close()
                except Exception:
                    pass
                delattr(self._local, conn_attr)

    def set_root_window(self, root_window):
        """设置主窗口引用"""
        self.root_window = root_window

    def execute_query(self, sql: str, params: tuple = ()) -> List[tuple]:
        """执行查询SQL并返回结果"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"[ERROR] 执行查询失败: {e}")
            return []

    def execute_update(self, sql: str, params: tuple = ()) -> bool:
        """执行更新SQL"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 执行更新失败: {e}")
            return False

    def execute_with_retry(self, func, operation_name="数据库操作", *args, **kwargs):
        """执行数据库操作，失败时重试"""
        import time
        max_retries = 3
        retry_count = 0

        while retry_count <= max_retries:
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower():
                    retry_count += 1
                    if retry_count > max_retries:
                        print(f"[ERROR] 数据库锁定重试超限: {operation_name}")
                        return None
                    print(f"[WARN] 数据库锁定，第 {retry_count}/{max_retries} 次重试")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except Exception as e:
                raise

    # ==================== 批次管理 ====================

    def create_batch(
        self,
        batch_name: str,
        customer_id: Optional[int],
        container_id: Optional[str],
        prefix: str,
        suffix: str,
        start_number: int,
        end_number: int,
        num_digits: Optional[int] = None,
        created_by: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[int]:
        """创建批次（批次和条码在同一事务中创建，确保原子性和 Cython 兼容性）"""
        try:
            total_count = end_number - start_number + 1
            # 如果没有指定位数，使用结束编号的位数
            if num_digits is None:
                num_digits = len(str(end_number))

            # 确保参数类型正确（Cython 兼容性修复）
            num_digits = int(num_digits)
            start_number = int(start_number)
            end_number = int(end_number)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 1. 插入批次记录
                cursor.execute("""
                    INSERT INTO batches (
                        batch_name, customer_id, container_id,
                        prefix, suffix, start_number, end_number,
                        total_count, created_by, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    batch_name, customer_id, container_id,
                    prefix, suffix, start_number, end_number,
                    total_count, created_by, notes, get_local_time_str(), get_local_time_str()
                ))
                batch_id = cursor.lastrowid

                # 2. 在同一连接中生成条码（避免 Cython 嵌套上下文管理器问题）
                barcodes = []
                for num in range(start_number, end_number + 1):
                    if num_digits > 0:
                        num_str = str(num).zfill(num_digits)
                    else:
                        num_str = str(num)
                    # 使用 str.format 替代 f-string（Cython 兼容性更好）
                    barcode_str = "{}{}{}".format(prefix, num_str, suffix)
                    barcodes.append((batch_id, barcode_str))

                if barcodes:
                    cursor.executemany("INSERT INTO barcodes (batch_id, barcode) VALUES (?, ?)", barcodes)

                # 3. 一次性提交（批次+条码原子操作）
                conn.commit()

                print("[INFO] 批次创建成功: {}, 条码数量: {}".format(batch_name, len(barcodes)))
                return batch_id

        except sqlite3.IntegrityError:
            print("[ERROR] 批次名称重复: {}".format(batch_name))
            return None
        except Exception as e:
            print("[ERROR] 创建批次失败: {}".format(e))
            traceback.print_exc()
            return None

    def _generate_barcodes_for_batch(self, batch_id: int, prefix: str, start: int, end: int, suffix: str, num_digits: int):
        """为批次生成条码数据（保留用于兼容，推荐使用 create_batch 内联生成）

        Args:
            num_digits: 编号位数。0表示不补零，直接用数字；>0表示补零到指定位数
        """
        try:
            # 确保参数类型正确（Cython 兼容）
            batch_id = int(batch_id)
            start = int(start)
            end = int(end)
            num_digits = int(num_digits)

            barcodes = []
            for num in range(start, end + 1):
                if num_digits > 0:
                    num_str = str(num).zfill(num_digits)
                else:
                    num_str = str(num)
                # 使用 str.format 替代 f-string
                barcode_str = "{}{}{}".format(prefix, num_str, suffix)
                barcodes.append((batch_id, barcode_str))

            print("[DEBUG] 生成条码数量: {}, range({}, {})".format(len(barcodes), start, end + 1))

            with self.get_connection() as conn:
                conn.executemany("INSERT INTO barcodes (batch_id, barcode) VALUES (?, ?)", barcodes)
                conn.commit()

        except Exception as e:
            print("[ERROR] 生成条码数据失败: {}".format(e))
            traceback.print_exc()
            raise

    def import_batch_from_excel(
        self,
        batch_name: str,
        customer_id: Optional[int],
        container_id: Optional[str],
        prefix: str,
        suffix: str,
        barcodes_data: list,
        created_by: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[int]:
        """从Excel导入批次"""
        try:
            import re
            numbers = []
            for bc_data in barcodes_data:
                barcode = bc_data['barcode']
                num_str = barcode.replace(prefix, '').replace(suffix, '')
                match = re.search(r'\d+', num_str)
                if match:
                    numbers.append(int(match.group()))

            start_number = min(numbers) if numbers else 1
            end_number = max(numbers) if numbers else len(barcodes_data)
            total_count = len(barcodes_data)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO batches (
                        batch_name, customer_id, container_id,
                        prefix, suffix, start_number, end_number,
                        total_count, created_by, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    batch_name, customer_id, container_id,
                    prefix, suffix, start_number, end_number,
                    total_count, created_by, notes, get_local_time_str(), get_local_time_str()
                ))

                batch_id = cursor.lastrowid
                barcode_records = []
                for bc_data in barcodes_data:
                    scan_time = bc_data.get('scan_time')
                    is_matched = bc_data.get('is_matched', False)
                    barcode_records.append((
                        batch_id, bc_data['barcode'], is_matched,
                        'pass' if is_matched else None,
                        bc_data['barcode'] if is_matched else None,
                        bc_data['barcode'] if is_matched else None,
                        scan_time
                    ))

                cursor.executemany("""
                    INSERT INTO barcodes (batch_id, barcode, is_matched, scan_result, front_code, back_code, scan_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, barcode_records)

                matched_count = sum(1 for bc in barcodes_data if bc.get('is_matched', False))
                cursor.execute("UPDATE batches SET matched_count = ? WHERE id = ?", (matched_count, batch_id))
                conn.commit()
                return batch_id

        except sqlite3.IntegrityError:
            print(f"[ERROR] 批次名称重复: {batch_name}")
            return None
        except Exception as e:
            print(f"[ERROR] 导入批次失败: {e}")
            traceback.print_exc()
            return None

    def get_batch_by_id(self, batch_id: int) -> Optional[Dict]:
        """获取批次信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.*, c.customer_name
                    FROM batches b LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE b.id = ?
                """, (batch_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[ERROR] 查询批次失败: {e}")
            return None

    def get_batch_by_name(self, batch_name: str) -> Optional[Dict]:
        """按批次名称查询"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.*, c.customer_name
                    FROM batches b LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE b.batch_name = ?
                """, (batch_name,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[ERROR] 查询批次失败: {e}")
            return None

    def update_batch_stats(self, batch_id: int):
        """更新批次统计"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM barcodes WHERE batch_id = ? AND is_matched = 1", (batch_id,))
                matched_count = cursor.fetchone()[0]

                cursor.execute("SELECT total_count, status FROM batches WHERE id = ?", (batch_id,))
                row = cursor.fetchone()
                if not row:
                    return

                total_count, current_status = row
                cursor.execute("""
                    UPDATE batches SET matched_count = ?, unmatched_count = total_count - ?, updated_at = ?
                    WHERE id = ?
                """, (matched_count, matched_count, get_local_time_str(), batch_id))
                conn.commit()
        except Exception as e:
            print(f"[ERROR] 更新批次统计失败: {e}")

    def archive_batch(self, batch_id: int, archived_by: Optional[int] = None) -> bool:
        """归档批次"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE batches SET status = 2, archived_at = ?, archived_by = ? WHERE id = ?
                """, (get_local_time_str(), archived_by, batch_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ERROR] 归档批次失败: {e}")
            return False

    def get_active_batches(self) -> List[Dict]:
        """获取所有活动批次"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.*, c.customer_name
                    FROM batches b LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE b.status = 1 ORDER BY b.created_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询活动批次失败: {e}")
            return []

    def query_batches(
        self,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        container_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """通用批次查询方法"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT b.*, c.customer_name FROM batches b LEFT JOIN customers c ON b.customer_id = c.id WHERE 1=1"
                params = []

                if status:
                    query += " AND b.status = ?"
                    params.append(status)
                if customer_id:
                    query += " AND b.customer_id = ?"
                    params.append(customer_id)
                if container_id:
                    query += " AND b.container_id LIKE ?"
                    params.append(f"%{container_id}%")

                query += " ORDER BY b.created_at DESC"
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询批次失败: {e}")
            return []

    # ==================== 条码管理 ====================

    def find_barcode(self, barcode: str) -> Optional[Dict]:
        """查找条码"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT bc.*, b.batch_name, b.customer_id, c.customer_name
                    FROM barcodes bc
                    JOIN batches b ON bc.batch_id = b.id
                    LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE bc.barcode = ?
                """, (barcode,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[ERROR] 查找条码失败: {e}")
            return None

    def update_barcode_status(
        self,
        barcode: str,
        is_matched: bool,
        front_code: Optional[str] = None,
        back_code: Optional[str] = None,
        scan_result: str = 'pass'
    ) -> bool:
        """更新条码匹配状态"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE barcodes SET is_matched = ?, scan_time = ?, scan_result = ?, front_code = ?, back_code = ?
                    WHERE barcode = ?
                """, (is_matched, get_local_time_str(), scan_result, front_code, back_code, barcode))

                rows_affected = cursor.rowcount
                conn.commit()

                if is_matched and rows_affected > 0:
                    cursor.execute("SELECT batch_id FROM barcodes WHERE barcode = ?", (barcode,))
                    row = cursor.fetchone()
                    if row:
                        self.update_batch_stats(row[0])

                return rows_affected > 0
        except Exception as e:
            print(f"[ERROR] 更新条码状态失败: {e}")
            return False

    def get_barcodes_by_batch(self, batch_id: int, is_matched: Optional[bool] = None) -> List[Dict]:
        """获取批次的所有条码"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if is_matched is None:
                    cursor.execute("SELECT * FROM barcodes WHERE batch_id = ? ORDER BY id", (batch_id,))
                else:
                    cursor.execute("SELECT * FROM barcodes WHERE batch_id = ? AND is_matched = ? ORDER BY id", (batch_id, is_matched))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询批次条码失败: {e}")
            return []

    # ==================== 扫描日志 ====================

    def log_scan(
        self,
        scanner_port: str,
        scan_data: str,
        scan_result: str,
        result_message: str,
        operator_id: Optional[int] = None,
        operator_name: Optional[str] = None
    ) -> bool:
        """
        记录扫码日志（每次扫码立即记录）

        Args:
            scanner_port: 扫码枪 (front/back)
            scan_data: 扫进来的原始数据
            scan_result: 结果类型 (waiting/pass/fail/duplicate/not_found/mismatch)
            result_message: 结果说明
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 先检查是否有新字段，没有则添加
                cursor.execute("PRAGMA table_info(scan_logs)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'scanner_port' not in columns:
                    cursor.execute("ALTER TABLE scan_logs ADD COLUMN scanner_port VARCHAR(10)")
                if 'scan_data' not in columns:
                    cursor.execute("ALTER TABLE scan_logs ADD COLUMN scan_data VARCHAR(100)")
                if 'result_message' not in columns:
                    cursor.execute("ALTER TABLE scan_logs ADD COLUMN result_message TEXT")

                cursor.execute("""
                    INSERT INTO scan_logs (scanner_port, scan_data, scan_result, result_message, operator_id, operator_name, scan_time, barcode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (scanner_port, scan_data, scan_result, result_message, operator_id, operator_name, get_local_time_str(), scan_data))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 记录扫码日志失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def insert_scan_log(
        self,
        batch_id: Optional[int],
        barcode: str,
        front_code: Optional[str],
        back_code: Optional[str],
        scan_result: str,
        error_message: Optional[str] = None,
        plc_signal: Optional[str] = None,
        operator_id: Optional[int] = None,
        operator_name: Optional[str] = None
    ) -> bool:
        """插入扫描日志（兼容旧接口）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scan_logs (batch_id, barcode, front_code, back_code, scan_result, error_message, plc_signal, operator_id, operator_name, scan_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (batch_id, barcode, front_code, back_code, scan_result, error_message, plc_signal, operator_id, operator_name, get_local_time_str()))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 插入扫描日志失败: {e}")
            return False

    def get_scan_logs(
        self,
        batch_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        scan_result: Optional[str] = None,
        scanner_port: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """查询扫描日志"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM scan_logs WHERE 1=1"
                params = []

                if batch_id:
                    query += " AND batch_id = ?"
                    params.append(batch_id)
                if start_time:
                    query += " AND scan_time >= ?"
                    params.append(start_time)
                if end_time:
                    query += " AND scan_time <= ?"
                    params.append(end_time)
                if scan_result:
                    query += " AND scan_result = ?"
                    params.append(scan_result)
                if scanner_port:
                    query += " AND scanner_port = ?"
                    params.append(scanner_port)

                query += " ORDER BY scan_time DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询扫描日志失败: {e}")
            return []

    # ==================== 统计查询 ====================

    def get_batch_stats(self, batch_id: int) -> Optional[Dict]:
        """获取批次统计信息"""
        try:
            batch = self.get_batch_by_id(batch_id)
            if not batch:
                return None
            return {
                'total': batch['total_count'],
                'matched': batch['matched_count'],
                'unmatched': batch['unmatched_count'],
                'batch_name': batch['batch_name'],
                'customer_name': batch.get('customer_name'),
                'container_id': batch['container_id'],
                'status': batch['status']
            }
        except Exception as e:
            print(f"[ERROR] 获取批次统计失败: {e}")
            return None

    def get_daily_stats(self, date: str) -> Dict:
        """获取每日统计"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM scan_logs WHERE DATE(scan_time) = ?", (date,))
                total_scans = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM scan_logs WHERE DATE(scan_time) = ? AND scan_result = 'pass'", (date,))
                pass_count = cursor.fetchone()[0]
                return {'date': date, 'total_scans': total_scans, 'pass_count': pass_count, 'fail_count': total_scans - pass_count}
        except Exception as e:
            print(f"[ERROR] 获取每日统计失败: {e}")
            return {}

    def query_by_customer(self, customer_id: int) -> List[Dict]:
        """按客户查询批次"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.*, c.customer_name FROM batches b JOIN customers c ON b.customer_id = c.id
                    WHERE b.customer_id = ? ORDER BY b.created_at DESC
                """, (customer_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 按客户查询失败: {e}")
            return []

    def query_by_container(self, container_id: str) -> List[Dict]:
        """按货柜批号查询批次"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.*, c.customer_name FROM batches b LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE b.container_id LIKE ? ORDER BY b.created_at DESC
                """, (f"%{container_id}%",))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 按货柜查询失败: {e}")
            return []

    def query_by_time_range(self, start_time: str, end_time: str, customer_id: Optional[int] = None) -> List[Dict]:
        """按时间范围查询扫码记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT bc.*, b.batch_name, b.container_id, c.customer_name
                    FROM barcodes bc JOIN batches b ON bc.batch_id = b.id LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE bc.scan_time BETWEEN ? AND ?
                """
                params = [start_time, end_time]
                if customer_id:
                    query += " AND b.customer_id = ?"
                    params.append(customer_id)
                query += " ORDER BY bc.scan_time DESC"
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 按时间查询失败: {e}")
            return []

    # ==================== 打印记录 ====================

    def insert_print_record(self, barcode: str, printer_name: str, barcode_type: str, print_status: str, error_message: Optional[str] = None) -> bool:
        """插入打印记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO print_records (barcode, printer_name, barcode_type, print_status, error_message) VALUES (?, ?, ?, ?, ?)",
                               (barcode, printer_name, barcode_type, print_status, error_message))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 插入打印记录失败: {e}")
            return False

    # ==================== 系统日志 ====================

    def insert_system_log(self, level: str, message: str, source: Optional[str] = None, created_at: Optional[str] = None) -> bool:
        """插入系统日志"""
        try:
            if not created_at:
                created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO system_logs (level, message, source, created_at) VALUES (?, ?, ?, ?)", (level, message, source, created_at))
                conn.commit()
                return True
        except Exception:
            return False

    def insert_system_logs_batch(self, logs: List[Dict]) -> bool:
        """批量插入系统日志"""
        if not logs:
            return True
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.executemany("INSERT INTO system_logs (level, message, source, created_at) VALUES (?, ?, ?, ?)",
                                   [(log['level'], log['message'], log.get('source'), log['created_at']) for log in logs])
                conn.commit()
                return True
        except Exception:
            return False

    def get_system_logs(self, start_date: Optional[str] = None, end_date: Optional[str] = None, level: Optional[str] = None, keyword: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """查询系统日志"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                conditions, params = [], []
                if start_date:
                    conditions.append("DATE(created_at) >= ?")
                    params.append(start_date)
                if end_date:
                    conditions.append("DATE(created_at) <= ?")
                    params.append(end_date)
                if level and level != "全部":
                    conditions.append("level = ?")
                    params.append(level)
                if keyword:
                    conditions.append("(message LIKE ? OR source LIKE ?)")
                    params.extend([f"%{keyword}%", f"%{keyword}%"])

                where_clause = " AND ".join(conditions) if conditions else "1=1"
                cursor.execute(f"SELECT * FROM system_logs WHERE {where_clause} ORDER BY created_at DESC LIMIT ?", params + [limit])
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询系统日志失败: {e}")
            return []

    def get_operation_logs(self, start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: Optional[int] = None, action: Optional[str] = None, keyword: Optional[str] = None, limit: int = 1000) -> List[Dict]:
        """查询操作日志"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                conditions, params = [], []
                if start_date:
                    conditions.append("DATE(created_at) >= ?")
                    params.append(start_date)
                if end_date:
                    conditions.append("DATE(created_at) <= ?")
                    params.append(end_date)
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                if action and action != "全部":
                    conditions.append("action = ?")
                    params.append(action)
                if keyword:
                    conditions.append("(username LIKE ? OR action LIKE ? OR details LIKE ?)")
                    params.extend([f"%{keyword}%"] * 3)

                where_clause = " AND ".join(conditions) if conditions else "1=1"
                cursor.execute(f"SELECT * FROM operation_logs WHERE {where_clause} ORDER BY created_at DESC LIMIT ?", params + [limit])
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询操作日志失败: {e}")
            return []

    # ==================== 打印配方管理 ====================

    def get_all_print_recipes(self) -> List[Dict]:
        """获取所有打印配方"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM print_recipes ORDER BY id")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询打印配方失败: {e}")
            return []

    def get_print_recipe_by_id(self, recipe_id: int) -> Optional[Dict]:
        """根据ID获取打印配方"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM print_recipes WHERE id = ?", (recipe_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[ERROR] 查询打印配方失败: {e}")
            return None

    def create_print_recipe(self, recipe_name: str, params: Dict) -> Optional[int]:
        """创建新打印配方"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO print_recipes (
                        recipe_name, barcode_type, label_width, label_height,
                        barcode_width, barcode_height, barcode_top_margin,
                        font_size, text_gap, auto_print_repeat_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recipe_name,
                    params.get('barcode_type', 'CODE39'),
                    params.get('label_width', 70.0),
                    params.get('label_height', 20.0),
                    params.get('barcode_width', 0.25),
                    params.get('barcode_height', 10.0),
                    params.get('barcode_top_margin', 2.0),
                    params.get('font_size', 12),
                    params.get('text_gap', -1.0),
                    params.get('auto_print_repeat_count', 1)
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"[ERROR] 配方名称重复: {recipe_name}")
            return None
        except Exception as e:
            print(f"[ERROR] 创建打印配方失败: {e}")
            return None

    def update_print_recipe(self, recipe_id: int, params: Dict) -> bool:
        """更新打印配方参数"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE print_recipes SET
                        barcode_type = ?, label_width = ?, label_height = ?,
                        barcode_width = ?, barcode_height = ?, barcode_top_margin = ?,
                        font_size = ?, text_gap = ?, auto_print_repeat_count = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    params.get('barcode_type', 'CODE39'),
                    params.get('label_width', 70.0),
                    params.get('label_height', 20.0),
                    params.get('barcode_width', 0.25),
                    params.get('barcode_height', 10.0),
                    params.get('barcode_top_margin', 2.0),
                    params.get('font_size', 12),
                    params.get('text_gap', -1.0),
                    params.get('auto_print_repeat_count', 1),
                    recipe_id
                ))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ERROR] 更新打印配方失败: {e}")
            return False

    def delete_print_recipe(self, recipe_id: int) -> bool:
        """删除打印配方"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM print_recipes WHERE id = ?", (recipe_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[ERROR] 删除打印配方失败: {e}")
            return False

    def get_log_statistics(self, log_type: str = "system", start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """获取日志统计信息"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                date_conditions, params = [], []
                if start_date:
                    date_conditions.append("DATE(created_at) >= ?")
                    params.append(start_date)
                if end_date:
                    date_conditions.append("DATE(created_at) <= ?")
                    params.append(end_date)

                where_clause = " AND ".join(date_conditions) if date_conditions else "1=1"

                if log_type == "system":
                    cursor.execute(f"""
                        SELECT COUNT(*) as total, SUM(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END) as error_count,
                        SUM(CASE WHEN level = 'WARNING' THEN 1 ELSE 0 END) as warning_count,
                        SUM(CASE WHEN level = 'INFO' THEN 1 ELSE 0 END) as info_count
                        FROM system_logs WHERE {where_clause}
                    """, params)
                else:
                    cursor.execute(f"""
                        SELECT COUNT(*) as total, COUNT(DISTINCT user_id) as user_count, COUNT(DISTINCT action) as action_count
                        FROM operation_logs WHERE {where_clause}
                    """, params)

                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception as e:
            print(f"[ERROR] 获取日志统计失败: {e}")
            return {}

    def clear_old_logs(self, log_type: str = "system", days: int = 30) -> bool:
        """清除旧日志"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                table = "system_logs" if log_type == "system" else "operation_logs"
                if days == 0:
                    cursor.execute(f"DELETE FROM {table}")
                else:
                    cursor.execute(f"DELETE FROM {table} WHERE created_at < datetime('now', '-{days} days')")
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 清除旧日志失败: {e}")
            return False

    def auto_cleanup_old_logs(self, system_days: int = 180, operation_days: int = 365) -> bool:
        """自动清理旧日志"""
        try:
            self.clear_old_logs(log_type="system", days=system_days)
            self.clear_old_logs(log_type="operation", days=operation_days)
            return True
        except Exception as e:
            print(f"[ERROR] 自动清理旧日志失败: {e}")
            return False

    def insert_operation_log(self, user_id: int, username: str, action: str, target_type: Optional[str] = None, target_id: Optional[int] = None, details: Optional[str] = None) -> bool:
        """插入操作日志"""
        try:
            with self.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO operation_logs (user_id, username, action, target_type, target_id, details) VALUES (?, ?, ?, ?, ?, ?)",
                               (user_id, username, action, target_type, target_id, details))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 插入操作日志失败: {e}")
            return False

    # ==================== 客户管理 ====================

    def get_all_customers(self, active_only: bool = True) -> List[Dict]:
        """获取所有客户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if active_only:
                    cursor.execute("SELECT * FROM customers WHERE is_active = 1 ORDER BY customer_name")
                else:
                    cursor.execute("SELECT * FROM customers ORDER BY customer_name")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[ERROR] 查询客户列表失败: {e}")
            return []

    def get_customer_by_id(self, customer_id: int) -> Optional[Dict]:
        """根据ID获取客户信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[ERROR] 查询客户失败: {e}")
            return None

    def add_customer(self, customer_name: str, notes: str = "", created_by: Optional[int] = None, **kwargs) -> Optional[int]:
        """添加新客户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO customers (customer_name, notes, created_by, created_at) VALUES (?, ?, ?, ?)",
                               (customer_name, notes, created_by, get_local_time_str()))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"[ERROR] 添加客户失败: {e}")
            return None

    def update_customer(self, customer_id: int, customer_name: Optional[str] = None, notes: Optional[str] = None, is_active: Optional[bool] = None, **kwargs) -> bool:
        """更新客户信息"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates, params = [], []
                if customer_name is not None:
                    updates.append("customer_name = ?")
                    params.append(customer_name)
                if notes is not None:
                    updates.append("notes = ?")
                    params.append(notes)
                if is_active is not None:
                    updates.append("is_active = ?")
                    params.append(1 if is_active else 0)
                if not updates:
                    return True
                params.append(customer_id)
                cursor.execute(f"UPDATE customers SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 更新客户失败: {e}")
            return False

    def delete_customer(self, customer_id: int) -> bool:
        """删除客户（软删除）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE customers SET is_active = 0 WHERE id = ?", (customer_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 删除客户失败: {e}")
            return False

    def activate_customer(self, customer_id: int) -> bool:
        """激活客户"""
        return self.update_customer(customer_id, is_active=True)


# 全局单例
db_manager = DatabaseManager()
