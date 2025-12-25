"""
扫码控制器 - PySide6版本
负责协调扫码验证的核心业务逻辑
"""

from datetime import datetime
from typing import Optional, Callable, Dict, Any
from PySide6.QtCore import QObject, Signal, QTimer
import threading

from .serial_handler import serial_handler
from .plc_handler import plc_handler
from .barcode_printer import barcode_printer
from .database_manager import DatabaseManager
from .ui_config_manager import UIConfigManager
from .time_utils import get_local_time_str
from .voice_announcer import get_voice_announcer


class ScanController(QObject):
    """扫码控制器 - 核心业务逻辑"""

    # ==================== Qt信号 ====================
    # 扫码状态更新
    front_code_received = Signal(str)  # 正面扫码数据
    back_code_received = Signal(str)  # 反面扫码数据

    # 验证结果
    verification_success = Signal(str, int, str)  # (barcode, batch_id, batch_name)
    verification_duplicate = Signal(str, int, str)  # (barcode, batch_id, batch_name) 重复扫码
    verification_failed = Signal(str, str)  # (barcode, error_message)
    verification_mismatch = Signal(str, str)  # (front_code, back_code) 二码不一致

    # 批次统计更新
    batch_stats_updated = Signal(int, int, int)  # (batch_id, matched_count, total_count)

    # 自动定位信号
    auto_locate_barcode = Signal(str, int, str)  # (barcode, batch_id, batch_name)

    # 设备状态
    device_status_changed = Signal(str, bool)  # (device_type, is_connected)

    # 日志信号
    log_message = Signal(str)

    # 扫码状态重置
    scan_status_reset = Signal()

    # 锁定状态信号（用于二码合一锁定）
    verification_lock_changed = Signal(bool, str)  # (is_locked, locked_code)

    def __init__(self, db_manager: DatabaseManager, ui_config: UIConfigManager):
        super().__init__()

        self.db_manager = db_manager
        self.ui_config = ui_config

        # 扫码状态
        self.front_code = ""
        self.back_code = ""
        self.front_code_info = None  # 正面条码的数据库信息
        self.back_code_info = None   # 反面条码的数据库信息

        # 扫码模式
        self._is_single_mode = False
        self._single_scan_step = "front"  # 单枪模式当前步骤

        # 二码合一锁定模式（第一面扫码匹配后锁定，等待另一面）
        self._verify_lock_mode = False           # 是否处于锁定模式
        self._verify_locked_code = ""            # 锁定的条码值
        self._verify_locked_side = ""            # 锁定时哪一面先扫（front/back）
        self._verify_locked_info = None          # 锁定时的条码数据库信息

        # 清空定时器
        self._clear_timer: Optional[QTimer] = None

        # 自动连接定时器
        self._auto_connect_timer: Optional[QTimer] = None

        # 打印机状态监控定时器
        self._printer_check_timer: Optional[QTimer] = None
        self._last_printer_status: bool = False

        # 连接串口信号
        serial_handler.data_received.connect(self._on_serial_data)
        serial_handler.connection_changed.connect(self._on_serial_connection_changed)
        serial_handler.set_log_callback(self._log)

        # 连接PLC信号
        plc_handler.connection_changed.connect(self._on_plc_connection_changed)
        plc_handler.set_log_callback(self._log)

        # 配置打印器
        barcode_printer._ui_config = ui_config
        barcode_printer._load_config()
        barcode_printer.set_log_callback(self._log)
        barcode_printer.print_completed.connect(self._on_print_completed)

        # 加载配置
        self._load_config()

        # 初始化语音播报器
        self._voice = get_voice_announcer(ui_config)

        # 启动打印机状态监控
        self._start_printer_status_monitor()

        # 延迟自动连接设备（等待UI初始化完成）
        self._auto_connect_timer = QTimer()
        self._auto_connect_timer.setSingleShot(True)
        self._auto_connect_timer.timeout.connect(self._auto_connect_devices)
        self._auto_connect_timer.start(2000)  # 2秒后自动连接

    def _log(self, message: str):
        """记录日志"""
        self.log_message.emit(message)
        print(message)

    def _load_config(self):
        """加载配置"""
        config = self.ui_config.get_scanner_config()
        self._is_single_mode = config.get('single_mode', False)

    # ==================== 设备连接 ====================

    def connect_scanner(self, port_key: str, port_name: str) -> bool:
        """连接扫码枪"""
        return serial_handler.connect(port_key, port_name)

    def disconnect_scanner(self, port_key: str):
        """断开扫码枪"""
        serial_handler.disconnect(port_key)

    def connect_plc(self, host: str, port: int) -> bool:
        """连接PLC"""
        return plc_handler.connect(host, port)

    def disconnect_plc(self):
        """断开PLC"""
        plc_handler.disconnect()

    def get_scanner_status(self, port_key: str) -> bool:
        """获取扫码枪连接状态"""
        return serial_handler.is_connected(port_key)

    def get_plc_status(self) -> bool:
        """获取PLC连接状态"""
        return plc_handler.is_connected()

    def send_to_plc(self, signal_type: str) -> bool:
        """发送信号到PLC"""
        return plc_handler.send_signal(signal_type)

    # ==================== 扫码模式 ====================

    def set_single_mode(self, enabled: bool):
        """设置单枪模式"""
        self._is_single_mode = enabled
        self._single_scan_step = "front"
        self._log(f"[INFO] 扫码模式已切换为: {'单枪模式' if enabled else '双枪模式'}")

    def is_single_mode(self) -> bool:
        """获取当前是否为单枪模式"""
        return self._is_single_mode

    # ==================== 串口数据处理 ====================

    def _on_serial_data(self, data: str, port_key: str):
        """处理串口接收的数据"""
        data = data.strip()
        if not data:
            return

        self._log(f"[SCAN] 收到 {port_key} 扫码: {data}")

        # 确定当前是正面还是反面
        if self._is_single_mode:
            # 单枪模式：交替判断
            current_side = self._single_scan_step
        else:
            # 双枪模式：根据端口判断
            current_side = port_key

        # 发送信号更新UI
        if current_side == "front":
            self.front_code_received.emit(data)
        else:
            self.back_code_received.emit(data)

        # ========== 二码合一锁定模式检查 ==========
        if self._verify_lock_mode and self._verify_locked_code:
            # 检查新扫码是否与锁定条码一致
            if data != self._verify_locked_code:
                # 条码不匹配锁定条码，报警并拒绝
                self._log(f"[ERROR] 锁定模式: 条码不匹配，锁定={self._verify_locked_code}，实际={data}")
                self.db_manager.log_scan(
                    scanner_port=current_side,
                    scan_data=data,
                    scan_result='lock_mismatch',
                    result_message=f'锁定条码不匹配，锁定: {self._verify_locked_code}'
                )
                self.send_to_plc("FAIL")
                self._voice.announce_lock_mismatch()
                self.verification_failed.emit(data, f"条码不匹配，锁定: {self._verify_locked_code}")
                # 不清空缓存，让用户重新扫正确的码覆盖
                return
            else:
                # 条码匹配锁定条码，正常进入缓存流程
                self._log(f"[OK] 锁定模式: {current_side} 条码匹配锁定码，继续验证")
                # 不return，继续进入正常缓存流程

        # 立即检查该条码状态（每次扫码都要单独查询）
        check_result = self._check_barcode_status(data)

        if check_result['status'] == 'not_found':
            # 条码不在活动批次中
            self._log(f"[ERROR] 条码不在活动批次中: {data}")
            # 立即记录日志
            self.db_manager.log_scan(
                scanner_port=current_side,
                scan_data=data,
                scan_result='not_found',
                result_message='不在活动批次'
            )
            self.send_to_plc("FAIL")
            self._voice.announce_invalid_code()  # 语音播报：条码无效
            self.verification_failed.emit(data, "不在活动批次")
            self._schedule_clear(2000)
            return

        elif check_result['status'] == 'already_matched':
            # 已匹配 → 重复扫码（但仍是有效码，传给打印系统判断）
            # 立即记录日志
            self.db_manager.log_scan(
                scanner_port=current_side,
                scan_data=data,
                scan_result='duplicate',
                result_message=f"重复扫码 (批次: {check_result.get('batch_name', '-')})"
            )
            # 有效码传给打印系统，由打印系统判断是否需要打印
            self._auto_print_on_scan(data, check_result.get('barcode_id'))
            self._voice.announce_duplicate_scan()  # 语音播报：重复扫码
            self._handle_duplicate_scan(data, check_result)
            return

        elif check_result['status'] == 'unmatched':
            # 未匹配 → 记录并等待另一面
            if current_side == "front":
                # 判断是否是第一把枪（另一面还没扫）
                is_first_scan = not self.back_code
                self.front_code = data
                self.front_code_info = check_result

                # 第一把枪扫码后立即进入锁定模式
                if is_first_scan:
                    self._enter_verify_lock_mode(data, current_side, check_result)
                    # 第一次扫码，播报"正面匹配"
                    self._voice.announce_front_matched()

                # 立即记录日志 - 等待反面
                self.db_manager.log_scan(
                    scanner_port=current_side,
                    scan_data=data,
                    scan_result='waiting',
                    result_message='等待反面扫码'
                )
                # 正面扫码时立即触发自动打印
                self._auto_print_on_scan(data, check_result.get('barcode_id'), current_side)

                if self._is_single_mode:
                    self._single_scan_step = "back"
                    self._log(f"[INFO] 单枪模式 - 正面已扫: {data}，请扫反面")
            else:
                # 判断是否是第一把枪（另一面还没扫）
                is_first_scan = not self.front_code
                self.back_code = data
                self.back_code_info = check_result

                # 第一把枪扫码后立即进入锁定模式
                if is_first_scan:
                    self._enter_verify_lock_mode(data, current_side, check_result)
                    # 第一次扫码，播报"反面匹配"
                    self._voice.announce_back_matched()

                # 立即记录日志 - 等待正面或准备验证
                self.db_manager.log_scan(
                    scanner_port=current_side,
                    scan_data=data,
                    scan_result='waiting',
                    result_message='等待正面扫码' if not self.front_code else '准备二码验证'
                )
                # 反面扫码时也触发自动打印
                self._auto_print_on_scan(data, check_result.get('barcode_id'), current_side)

                if self._is_single_mode:
                    self._single_scan_step = "front"
                    self._log(f"[INFO] 单枪模式 - 反面已扫: {data}")

            # 检查是否可以进行二码合一验证
            self._try_dual_code_verification()

    def _check_barcode_status(self, barcode: str) -> dict:
        """
        检查单个条码的状态

        Returns:
            {
                'status': 'not_found' | 'already_matched' | 'unmatched',
                'barcode_id': int,
                'batch_id': int,
                'batch_name': str,
                'scan_count': int
            }
        """
        try:
            result = self.db_manager.execute_query("""
                SELECT bc.id, bc.batch_id, b.batch_name, bc.is_matched, bc.scan_count
                FROM barcodes bc
                JOIN batches b ON bc.batch_id = b.id
                WHERE bc.barcode = ? AND b.status = 1
                LIMIT 1
            """, (barcode,))

            if not result:
                return {'status': 'not_found'}

            barcode_id, batch_id, batch_name, is_matched, scan_count = result[0]

            if is_matched == 1:
                return {
                    'status': 'already_matched',
                    'barcode_id': barcode_id,
                    'batch_id': batch_id,
                    'batch_name': batch_name,
                    'scan_count': scan_count or 0
                }
            else:
                return {
                    'status': 'unmatched',
                    'barcode_id': barcode_id,
                    'batch_id': batch_id,
                    'batch_name': batch_name,
                    'scan_count': scan_count or 0
                }

        except Exception as e:
            self._log(f"[ERROR] 查询条码状态失败: {e}")
            return {'status': 'not_found'}

    def _handle_duplicate_scan(self, barcode: str, info: dict):
        """处理重复扫码（条码已匹配的情况）"""
        try:
            scan_time = get_local_time_str()
            new_scan_count = info['scan_count'] + 1

            # 更新scan_count
            self.db_manager.execute_update("""
                UPDATE barcodes SET scan_count = ? WHERE id = ?
            """, (new_scan_count, info['barcode_id']))

            # 日志已在 _on_serial_data 中立即记录

            self._log(f"[WARN] 重复扫码: {barcode} (批次: {info['batch_name']}, 重复次数: {new_scan_count})")
            self.send_to_plc("FAIL")
            self.verification_duplicate.emit(barcode, info['batch_id'], info['batch_name'])

            # 发送自动定位信号
            self.auto_locate_barcode.emit(barcode, info['batch_id'], info['batch_name'])

            # 更新批次统计显示
            stats = self.db_manager.execute_query("""
                SELECT total_count, matched_count FROM batches WHERE id = ?
            """, (info['batch_id'],))
            if stats:
                self.batch_stats_updated.emit(info['batch_id'], stats[0][1], stats[0][0])

            self._schedule_clear(2000)

        except Exception as e:
            self._log(f"[ERROR] 处理重复扫码失败: {e}")
            self._schedule_clear(2000)

    def _try_dual_code_verification(self):
        """尝试进行二码合一验证"""
        # 检查正反面是否都有数据
        if not self.front_code or not self.back_code:
            return  # 等待另一面扫码

        # 检查正反面是否一致
        if self.front_code != self.back_code:
            self._log(f"[ERROR] 二码不一致: 正面={self.front_code}, 反面={self.back_code}")
            # 记录日志 - 二码不一致（更新之前的waiting记录说明）
            self.db_manager.log_scan(
                scanner_port='verify',
                scan_data=f"{self.front_code} vs {self.back_code}",
                scan_result='mismatch',
                result_message=f'二码不一致: 正面={self.front_code}, 反面={self.back_code}'
            )
            self.send_to_plc("FAIL")
            self._voice.announce_mismatch()  # 语音播报：二码不一致
            self.verification_mismatch.emit(self.front_code, self.back_code)
            self._schedule_clear(2000)
            return

        # 正反面一致，执行首次验证
        self._voice.announce_match_success()  # 语音播报：匹配成功
        self._mark_as_first_verified(self.front_code, self.front_code_info)

    def _on_serial_connection_changed(self, port_key: str, is_connected: bool):
        """串口连接状态变化"""
        self.device_status_changed.emit(port_key, is_connected)

    def _on_plc_connection_changed(self, is_connected: bool):
        """PLC连接状态变化"""
        self.device_status_changed.emit("plc", is_connected)

    def _mark_as_first_verified(self, barcode: str, info: dict):
        """
        首次验证条码（二码合一验证通过后调用）
        此时条码状态已确认为未匹配(unmatched)
        验证成功后解锁，允许下一个循环
        """
        try:
            # 二码合一验证成功，先解锁
            self._exit_verify_lock_mode()

            scan_time = get_local_time_str()
            barcode_id = info['barcode_id']
            batch_id = info['batch_id']
            batch_name = info['batch_name']

            # 首次验证成功：设置 is_matched=1
            self.db_manager.execute_update("""
                UPDATE barcodes
                SET is_matched = 1, scan_time = ?, scan_count = 0,
                    front_code = ?, back_code = ?
                WHERE id = ?
            """, (scan_time, self.front_code, self.back_code, barcode_id))

            # 更新批次统计
            self.db_manager.execute_update("""
                UPDATE batches
                SET matched_count = matched_count + 1
                WHERE id = ?
            """, (batch_id,))

            # 记录扫描日志 - 验证通过
            self.db_manager.log_scan(
                scanner_port='verify',
                scan_data=barcode,
                scan_result='pass',
                result_message=f'二码验证通过 (批次: {batch_name})'
            )

            self._log(f"[OK] 二码验证通过: {barcode} (批次: {batch_name})")
            self.send_to_plc("PASS")
            self.verification_success.emit(barcode, batch_id, batch_name)

            # 查询最新的批次统计
            stats = self.db_manager.execute_query("""
                SELECT total_count, matched_count
                FROM batches WHERE id = ?
            """, (batch_id,))

            if stats:
                total_count, matched_count = stats[0]
                self.batch_stats_updated.emit(batch_id, matched_count, total_count)

            # 发送自动定位信号
            self.auto_locate_barcode.emit(barcode, batch_id, batch_name)

            # 注意：自动打印已在扫码时触发，验证成功后不再重复打印

            # 延迟清空扫码数据
            self._schedule_clear(2000)

        except Exception as e:
            self._log(f"[ERROR] 验证异常: {e}")
            # 记录日志 - 验证异常也要留痕！
            try:
                self.db_manager.log_scan(
                    scanner_port='verify',
                    scan_data=barcode,
                    scan_result='fail',
                    result_message=f'验证异常: {str(e)}'
                )
            except:
                pass  # 日志记录失败不影响主流程
            self.send_to_plc("FAIL")
            self.verification_failed.emit(barcode, "验证异常")
            self._schedule_clear(2000)

    def _auto_print_on_scan(self, barcode: str, barcode_id: int, trigger_side: str = "front"):
        """扫码时立即触发自动打印（不分正反面，扫哪个打哪个）

        Args:
            barcode: 条码内容
            barcode_id: 条码ID
            trigger_side: 触发打印的扫码枪（front/back）
        """
        if not barcode or not barcode_id:
            return

        try:
            # 检查打印功能是否启用
            if not barcode_printer.is_enabled():
                return

            # 查询是否已打印
            result = self.db_manager.execute_query("""
                SELECT is_printed FROM barcodes WHERE id = ?
            """, (barcode_id,))

            if not result:
                return

            is_printed = result[0][0]
            if is_printed:
                self._log(f"[INFO] 条码已打印过，跳过: {barcode}")
                return

            # 立即执行打印
            self._log(f"[INFO] 扫码触发自动打印: {barcode}")
            success = barcode_printer.print_barcode(barcode)

            if success:
                # 打印成功，更新数据库
                print_time = get_local_time_str()
                self.db_manager.execute_update("""
                    UPDATE barcodes
                    SET is_printed = 1, last_print_time = ?
                    WHERE id = ?
                """, (print_time, barcode_id))
                self._log(f"[OK] 扫码打印成功: {barcode}")
                # 注意：锁定模式已在第一面扫码时触发，不再在此处触发
            else:
                self._log(f"[WARN] 扫码打印失败: {barcode}")

        except Exception as e:
            self._log(f"[ERROR] 扫码自动打印失败: {e}")

    def _check_and_print(self, barcode: str, barcode_id: int):
        """检查条码是否需要打印，如果需要则打印（保留用于手动调用）"""
        try:
            # 查询是否已打印
            result = self.db_manager.execute_query("""
                SELECT is_printed FROM barcodes WHERE id = ?
            """, (barcode_id,))

            if not result:
                return

            is_printed = result[0][0]

            if is_printed:
                self._log(f"[INFO] 条码已打印过，跳过: {barcode}")
                return

            # 检查打印功能是否启用
            if not barcode_printer.is_enabled():
                self._log(f"[INFO] 打印功能未启用，跳过: {barcode}")
                return

            # 执行打印
            self._log(f"[INFO] 开始自动打印: {barcode}")
            success = barcode_printer.print_barcode(barcode)

            if success:
                # 打印成功，更新数据库
                print_time = get_local_time_str()
                self.db_manager.execute_update("""
                    UPDATE barcodes
                    SET is_printed = 1, last_print_time = ?
                    WHERE id = ?
                """, (print_time, barcode_id))
                self._log(f"[OK] 条码打印成功并已标记: {barcode}")
            else:
                self._log(f"[WARN] 条码打印失败: {barcode}")

        except Exception as e:
            self._log(f"[ERROR] 自动打印检查失败: {e}")

    def _on_print_completed(self, barcode: str, success: bool):
        """打印完成回调"""
        self.print_completed.emit(barcode, success)

    # ==================== 二码合一锁定模式管理 ====================

    def _enter_verify_lock_mode(self, barcode: str, side: str, info: dict):
        """进入二码合一锁定模式（第一面扫码匹配后立即锁定）

        Args:
            barcode: 锁定的条码
            side: 触发锁定的扫码枪（front/back）
            info: 条码数据库信息
        """
        self._verify_lock_mode = True
        self._verify_locked_code = barcode
        self._verify_locked_side = side
        self._verify_locked_info = info
        self._log(f"[INFO] 进入锁定模式，锁定条码: {barcode}，{side}枪先扫")
        self.verification_lock_changed.emit(True, barcode)

    def _exit_verify_lock_mode(self):
        """退出二码合一锁定模式"""
        old_code = self._verify_locked_code
        self._verify_lock_mode = False
        self._verify_locked_code = ""
        self._verify_locked_side = ""
        self._verify_locked_info = None
        self._log(f"[INFO] 退出锁定模式，原锁定条码: {old_code}")
        self.verification_lock_changed.emit(False, "")

    def is_verify_locked(self) -> bool:
        """检查是否处于锁定模式"""
        return self._verify_lock_mode

    def get_verify_locked_code(self) -> str:
        """获取当前锁定的条码"""
        return self._verify_locked_code if self._verify_lock_mode else ""

    def set_verify_lock_mode(self, enabled: bool):
        """设置锁定模式开关"""
        if enabled and not self._verify_lock_mode:
            # 开启锁定模式但不锁定具体条码（等待第一次扫码匹配）
            pass
        elif not enabled and self._verify_lock_mode:
            # 关闭锁定模式时先解锁
            self.manual_unlock_verify()

    def manual_unlock_verify(self):
        """手动解锁锁定模式"""
        if self._verify_lock_mode:
            self._log(f"[INFO] 手动解锁锁定模式")
            self._exit_verify_lock_mode()

    def _schedule_clear(self, delay_ms: int):
        """延迟清空扫码数据"""
        if self._clear_timer:
            self._clear_timer.stop()

        self._clear_timer = QTimer()
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._clear_scan_codes)
        self._clear_timer.start(delay_ms)

    def _clear_scan_codes(self):
        """清空扫码数据"""
        self.front_code = ""
        self.back_code = ""
        self.front_code_info = None
        self.back_code_info = None
        self._single_scan_step = "front"
        # 确保锁定状态也被清除
        if self._verify_lock_mode:
            self._exit_verify_lock_mode()
        self.scan_status_reset.emit()

    # ==================== 手动操作 ====================

    def manual_verify(self, barcode: str) -> bool:
        """手动验证条码（用于测试）"""
        # 模拟正面扫码
        self._on_serial_data(barcode, "front")
        # 模拟反面扫码
        self._on_serial_data(barcode, "back")
        return True

    def reset_scan(self):
        """手动重置扫码状态"""
        self._clear_scan_codes()
        self._log("[INFO] 扫码状态已重置")

    # ==================== 打印机状态监控 ====================

    def _start_printer_status_monitor(self):
        """启动打印机状态监控"""
        self._printer_check_timer = QTimer()
        self._printer_check_timer.timeout.connect(self._check_printer_status)
        self._printer_check_timer.start(5000)  # 每5秒检测一次

    def _check_printer_status(self):
        """检查打印机状态"""
        try:
            printer_name = barcode_printer.get_selected_printer()
            if not printer_name:
                is_available = False
            else:
                # 检查打印机是否在列表中
                available_printers = barcode_printer.list_printers()
                is_available = printer_name in available_printers

            # 状态变化时发送信号
            if is_available != self._last_printer_status:
                self._last_printer_status = is_available
                self.device_status_changed.emit("printer", is_available)
                if is_available:
                    self._log(f"[INFO] 打印机已连接: {printer_name}")
                else:
                    self._log(f"[WARN] 打印机离线或未配置")
        except Exception as e:
            if self._last_printer_status:
                self._last_printer_status = False
                self.device_status_changed.emit("printer", False)

    def get_printer_status(self) -> bool:
        """获取打印机状态"""
        return self._last_printer_status

    # ==================== 自动连接 ====================

    def _auto_connect_devices(self):
        """自动连接设备（在子线程中执行，避免阻塞UI）"""
        thread = threading.Thread(target=self._auto_connect_devices_worker, daemon=True)
        thread.start()

    def _auto_connect_devices_worker(self):
        """自动连接设备的工作线程"""
        try:
            self._log("[INFO] 开始自动连接设备...")

            # 1. 自动连接PLC
            plc_config = self.ui_config.get_plc_config()
            plc_ip = plc_config.get('ip', '192.168.0.5')
            plc_port = int(plc_config.get('port', 502))
            self._log(f"[INFO] 尝试连接PLC: {plc_ip}:{plc_port}")
            plc_success = self.connect_plc(plc_ip, plc_port)
            if plc_success:
                self._log(f"[OK] PLC连接成功")
            else:
                self._log(f"[WARN] PLC连接失败，可能需要手动配置")

            # 2. 自动连接扫码枪
            scanner_config = self.ui_config.get_scanner_config()
            front_port = scanner_config.get('front_port', '')
            back_port = scanner_config.get('back_port', '')
            single_mode = scanner_config.get('single_mode', False)

            self._is_single_mode = single_mode

            if front_port:
                self._log(f"[INFO] 尝试连接正面扫码枪: {front_port}")
                front_success = self.connect_scanner("front", front_port)
                if front_success:
                    self._log(f"[OK] 正面扫码枪连接成功")
                else:
                    self._log(f"[WARN] 正面扫码枪连接失败")

            if not single_mode and back_port:
                self._log(f"[INFO] 尝试连接反面扫码枪: {back_port}")
                back_success = self.connect_scanner("back", back_port)
                if back_success:
                    self._log(f"[OK] 反面扫码枪连接成功")
                else:
                    self._log(f"[WARN] 反面扫码枪连接失败")

            # 3. 检查打印机状态
            self._check_printer_status()

            self._log("[INFO] 设备自动连接完成")

        except Exception as e:
            self._log(f"[ERROR] 设备自动连接异常: {e}")

    # ==================== 资源清理 ====================

    def cleanup(self):
        """清理资源"""
        serial_handler.disconnect_all()
        plc_handler.disconnect()
        if self._clear_timer:
            self._clear_timer.stop()
        if self._auto_connect_timer:
            self._auto_connect_timer.stop()
        if self._printer_check_timer:
            self._printer_check_timer.stop()
        if self._voice:
            self._voice.cleanup()
