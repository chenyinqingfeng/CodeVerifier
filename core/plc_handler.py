"""
PLC通信模块 - PySide6版本
负责与PLC通过Modbus TCP通信
"""

import logging
from typing import Optional, Callable, Tuple
from PySide6.QtCore import QObject, Signal

# 屏蔽pymodbus库的日志输出
logging.getLogger('pymodbus').setLevel(logging.CRITICAL)

try:
    from pymodbus.client import ModbusTcpClient
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False
    ModbusTcpClient = None


class PLCHandler(QObject):
    """PLC通信处理器"""

    # Qt信号
    connection_changed = Signal(bool)  # is_connected
    send_completed = Signal(str, bool)  # (signal_type, success)

    def __init__(self):
        super().__init__()
        self._host = "192.168.0.5"
        self._port = 502
        self._address = 0
        self._is_connected = False
        self._log_callback: Optional[Callable] = None

    def set_log_callback(self, callback: Callable):
        """设置日志回调"""
        self._log_callback = callback

    def _log(self, message: str):
        """记录日志"""
        if self._log_callback:
            self._log_callback(message)
        print(message)

    @property
    def is_available(self) -> bool:
        """检查pymodbus是否可用"""
        return PYMODBUS_AVAILABLE

    def get_config(self) -> Tuple[str, int]:
        """获取当前配置"""
        return (self._host, self._port)

    def set_config(self, host: str, port: int):
        """设置PLC连接配置"""
        self._host = host
        self._port = port

    def is_connected(self) -> bool:
        """获取连接状态"""
        return self._is_connected

    def connect(self, host: Optional[str] = None, port: Optional[int] = None) -> bool:
        """
        连接PLC

        Args:
            host: PLC IP地址（可选，不传则使用已配置的值）
            port: PLC端口（可选，不传则使用已配置的值）

        Returns:
            是否连接成功
        """
        if not PYMODBUS_AVAILABLE:
            self._log("[ERROR] [PLC] pymodbus库未安装，无法连接PLC")
            return False

        if host:
            self._host = host
        if port:
            self._port = port

        try:
            client = ModbusTcpClient(self._host, port=self._port, timeout=3)
            if client.connect():
                self._log(f"[OK] [PLC] 连接成功: {self._host}:{self._port}")
                client.close()
                self._is_connected = True
                self.connection_changed.emit(True)
                return True
            else:
                self._log(f"[ERROR] [PLC] 无法连接到 {self._host}:{self._port}")
                self._is_connected = False
                self.connection_changed.emit(False)
                return False
        except Exception as e:
            self._log(f"[ERROR] [PLC] 连接异常: {e}")
            self._is_connected = False
            self.connection_changed.emit(False)
            return False

    def disconnect(self):
        """断开PLC连接"""
        self._is_connected = False
        self.connection_changed.emit(False)
        self._log("[INFO] [PLC] 已断开连接")

    def test_connection(self) -> bool:
        """测试PLC连接"""
        return self.connect()

    def send_pass(self) -> bool:
        """发送PASS信号（值=1）"""
        return self._write_register(1, "PASS")

    def send_fail(self) -> bool:
        """发送FAIL信号（值=2）"""
        return self._write_register(2, "FAIL")

    def send_signal(self, signal_type: str) -> bool:
        """
        发送信号到PLC

        Args:
            signal_type: "PASS" 或 "FAIL"

        Returns:
            是否发送成功
        """
        if signal_type.upper() == "PASS":
            return self.send_pass()
        else:
            return self.send_fail()

    def send_value(self, value: int) -> bool:
        """发送自定义数值到PLC"""
        return self._write_register(value, f"VALUE({value})")

    def _write_register(self, value: int, signal_name: str = "") -> bool:
        """
        写入寄存器

        Args:
            value: 要写入的值
            signal_name: 信号名称（用于日志）

        Returns:
            是否写入成功
        """
        if not PYMODBUS_AVAILABLE:
            self._log(f"[ERROR] [PLC] pymodbus库未安装，无法发送 {signal_name}")
            self.send_completed.emit(signal_name, False)
            return False

        try:
            client = ModbusTcpClient(self._host, port=self._port, timeout=2)
            if client.connect():
                client.write_register(self._address, int(value))
                self._log(f"[INFO] [PLC] 发送 {signal_name} (值={value}) 到 {self._host} 成功")
                client.close()
                self._is_connected = True
                self.connection_changed.emit(True)
                self.send_completed.emit(signal_name, True)
                return True
            else:
                self._log(f"[ERROR] [PLC] 无法连接到 {self._host}:{self._port}")
                self._is_connected = False
                self.connection_changed.emit(False)
                self.send_completed.emit(signal_name, False)
                return False
        except Exception as e:
            self._log(f"[ERROR] [PLC] 发送 {signal_name} 失败: {e}")
            self._is_connected = False
            self.connection_changed.emit(False)
            self.send_completed.emit(signal_name, False)
            return False


# 全局单例
plc_handler = PLCHandler()
