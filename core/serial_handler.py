"""
串口处理模块 - PySide6版本
负责扫码枪串口通信
"""

import serial
import serial.tools.list_ports
import threading
from typing import Optional, Callable, Dict
from PySide6.QtCore import QObject, Signal


# 默认波特率
BAUDRATE = 38400


class SerialHandler(QObject):
    """串口处理器 - 使用Qt信号进行线程安全的UI更新"""

    # Qt信号
    data_received = Signal(str, str)  # (data, port_key)
    connection_changed = Signal(str, bool)  # (port_key, is_connected)
    error_occurred = Signal(str, str)  # (port_key, error_message)

    def __init__(self):
        super().__init__()
        self._serial_connections: Dict[str, serial.Serial] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event] = {
            "front": threading.Event(),
            "back": threading.Event()
        }
        self._connection_status: Dict[str, bool] = {
            "front": False,
            "back": False
        }
        self._log_callback: Optional[Callable] = None

    def set_log_callback(self, callback: Callable):
        """设置日志回调"""
        self._log_callback = callback

    def _log(self, message: str):
        """记录日志"""
        if self._log_callback:
            self._log_callback(message)
        print(message)

    @staticmethod
    def list_ports() -> list:
        """列出所有可用串口"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'display': f"{port.device} - {port.description}"
            })
        return ports if ports else []

    def get_connection_status(self, port_key: str) -> bool:
        """获取串口连接状态"""
        return self._connection_status.get(port_key, False)

    def is_connected(self, port_key: str) -> bool:
        """检查串口是否已连接"""
        return self._connection_status.get(port_key, False)

    def connect(self, port_key: str, port_name: str) -> bool:
        """
        连接串口

        Args:
            port_key: 端口标识 ("front" 或 "back")
            port_name: 串口名称 (如 "COM20")

        Returns:
            是否连接成功
        """
        # 先断开已有连接
        if self._connection_status.get(port_key):
            self.disconnect(port_key)

        if not port_name or port_name == "N/A":
            self._log(f"[WARN] 串口 {port_key} 未配置")
            return False

        # 重置停止标志
        self._stop_flags[port_key].clear()

        # 启动监听线程
        thread = threading.Thread(
            target=self._listen_thread,
            args=(port_key, port_name),
            daemon=True
        )
        self._threads[port_key] = thread
        thread.start()

        # 等待连接结果（最多2秒）
        for _ in range(20):
            if self._connection_status.get(port_key):
                return True
            if self._stop_flags[port_key].is_set():
                return False
            threading.Event().wait(0.1)

        return self._connection_status.get(port_key, False)

    def disconnect(self, port_key: str):
        """断开串口连接"""
        # 设置停止标志
        self._stop_flags[port_key].set()

        # 等待线程结束
        thread = self._threads.get(port_key)
        if thread and thread.is_alive():
            thread.join(timeout=1.0)

        # 关闭串口
        ser = self._serial_connections.get(port_key)
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass

        self._connection_status[port_key] = False
        self._serial_connections.pop(port_key, None)
        self._threads.pop(port_key, None)

        self.connection_changed.emit(port_key, False)
        self._log(f"[INFO] 串口 {port_key} 已断开")

    def disconnect_all(self):
        """断开所有串口"""
        for port_key in list(self._threads.keys()):
            self.disconnect(port_key)

    def _listen_thread(self, port_key: str, port_name: str):
        """串口监听线程"""
        ser = None
        try:
            # 尝试连接串口
            ser = serial.Serial(port_name, BAUDRATE, timeout=0.1)
            self._serial_connections[port_key] = ser
            self._connection_status[port_key] = True

            self._log(f"[OK] 串口 {port_name} ({port_key}) 已连接 @{BAUDRATE}bps")
            self.connection_changed.emit(port_key, True)

            buffer = b""

            # 持续监听数据
            while not self._stop_flags[port_key].is_set():
                try:
                    # 读取可用数据
                    data = ser.read(ser.in_waiting or 1)
                    if data:
                        buffer += data

                        # 检测多种结束符：CR+LF 或 Tab
                        while b'\r\n' in buffer or b'\t' in buffer:
                            if b'\r\n' in buffer and (b'\t' not in buffer or buffer.find(b'\r\n') < buffer.find(b'\t')):
                                line_bytes, buffer = buffer.split(b'\r\n', 1)
                            else:
                                line_bytes, buffer = buffer.split(b'\t', 1)

                            # 处理接收到的完整数据
                            line_str = line_bytes.decode('utf-8', errors='ignore').strip()
                            if line_str:
                                self.data_received.emit(line_str, port_key)

                except serial.SerialException:
                    break

        except serial.SerialException as e:
            self._connection_status[port_key] = False
            self.connection_changed.emit(port_key, False)
            self.error_occurred.emit(port_key, f"串口连接失败: {e}")
            self._log(f"[ERROR] 串口 {port_name} ({port_key}) 连接失败: {e}")

        except Exception as e:
            self._connection_status[port_key] = False
            self.connection_changed.emit(port_key, False)
            self.error_occurred.emit(port_key, f"串口异常: {e}")
            self._log(f"[ERROR] 串口 {port_name} ({port_key}) 异常: {e}")

        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass
            self._connection_status[port_key] = False
            self._serial_connections.pop(port_key, None)


# 全局单例
serial_handler = SerialHandler()
