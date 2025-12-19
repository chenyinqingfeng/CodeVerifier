# -*- coding: utf-8 -*-
"""
安全检测模块 - 反虚拟机、反调试
"""

import sys
import ctypes
import subprocess
from PySide6.QtCore import QTimer

# 缓存虚拟机检测结果（虚拟机状态不会变）
_vm_cache = None


def _clear_device_identity():
    """清除设备身份信息（设备ID和激活密钥）"""
    try:
        from .state_manager import app_state
        # 删除所有设备身份相关的数据
        app_state.update({
            "device_id": "",
            "license_key": "",
            "uuid_ref": "",
            "device_rand": ""
        })
    except Exception:
        pass  # 静默失败，不暴露任何信息

def is_debugger_present() -> bool:
    """检测调试器"""
    try:
        # Windows API检测
        if sys.platform == 'win32':
            return ctypes.windll.kernel32.IsDebuggerPresent() != 0
    except:
        pass
    return False

def is_virtual_machine() -> bool:
    """检测虚拟机"""
    try:
        # 检查常见虚拟机特征
        # 1. 检查系统制造商
        result = subprocess.run(
            ['wmic', 'computersystem', 'get', 'manufacturer,model'],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        output = result.stdout.lower()

        vm_keywords = ['vmware', 'virtualbox', 'virtual', 'qemu', 'xen', 'hyper-v', 'kvm']
        for keyword in vm_keywords:
            if keyword in output:
                return True

        # 2. 检查BIOS信息
        result = subprocess.run(
            ['wmic', 'bios', 'get', 'serialnumber,version'],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        output = result.stdout.lower()
        for keyword in vm_keywords:
            if keyword in output:
                return True

    except:
        pass
    return False

def check_security() -> tuple:
    """
    执行安全检测
    返回: (是否安全, 错误信息)
    """
    if is_debugger_present():
        return False, "debugger"

    if is_virtual_machine():
        return False, "vm"

    if not verify_pubkey_integrity():
        return False, "tampered"

    return True, ""


class SecurityGuard:
    """安全守护 - 持续检测"""

    _instance = None

    def __init__(self):
        self._timer = QTimer()
        self._timer.timeout.connect(self._check)

    @classmethod
    def start(cls, interval_ms=3000):
        """启动持续检测，默认3秒一次"""
        if cls._instance is None:
            cls._instance = cls()
        cls._instance._timer.start(interval_ms)

    @classmethod
    def stop(cls):
        """停止检测"""
        if cls._instance:
            cls._instance._timer.stop()

    def _check(self):
        """定时检测"""
        if is_debugger_present():
            _clear_device_identity()  # 清除设备身份
            sys.exit(0)


def timing_check(func):
    """装饰器：检测函数执行时间异常（单步调试会很慢）"""
    import time
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        # 正常执行应该很快，超过2秒说明被调试
        if elapsed > 2.0:
            _clear_device_identity()  # 清除设备身份
            sys.exit(0)
        return result
    return wrapper


def verify_pubkey_integrity() -> bool:
    """验证公钥完整性，防止被替换"""
    from .state_manager import ED25519_PUBKEY_PEM
    import hashlib
    expected_hash = "70ee151f"
    actual_hash = hashlib.md5(ED25519_PUBKEY_PEM).hexdigest()[:8]
    return actual_hash == expected_hash
