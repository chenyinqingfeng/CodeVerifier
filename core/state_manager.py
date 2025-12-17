"""
AppState - 应用状态管理器
版本: 3.0 (PySide6版本)
"""

import base64
import hashlib
import json
import os
import platform
import re
import secrets
import subprocess
from typing import Tuple, Dict
import uuid

try:
    import winreg
except Exception:
    winreg = None

ED25519_PUBKEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAQP/CVFSjsRYTJRawPA1Genp2SRBuZXxWduc2UNt+scw=
-----END PUBLIC KEY-----"""
APP_SALT = "YourApp-DeviceID-Salt-2025"
_INVALID_MARKS = {"", "0", "00000000", "0000000000000000", "DEFAULT STRING", "TO BE FILLED BY O.E.M.", "SYSTEM SERIAL NUMBER", "BASE BOARD SERIAL NUMBER", "NONE", "UNKNOWN"}
_B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def _clean_hw(s: str) -> str:
    s = (s or "").strip().upper()
    return re.sub(r"[^A-Z0-9\-:]", "", s)


def _read_machine_guid() -> str:
    """优先使用注册表 MachineGuid"""
    if not winreg:
        return ""
    subkey = r"SOFTWARE\Microsoft\Cryptography"
    for access in (winreg.KEY_READ | 0x0100, winreg.KEY_READ | 0x0200):
        try:
            h = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey, 0, access)
            val, _ = winreg.QueryValueEx(h, "MachineGuid")
            winreg.CloseKey(h)
            v = _clean_hw(str(val))
            if v and v not in _INVALID_MARKS:
                return v
        except OSError:
            continue
    return ""


def _read_wmic_single_timeout(cmd: list, skip_head: str, timeout_sec: float = 1.0) -> str:
    """短超时 WMIC"""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=timeout_sec,
        )
        if out.returncode == 0:
            vals = [x.strip() for x in out.stdout.splitlines() if x.strip() and skip_head.upper() not in x.upper()]
            if vals:
                v = _clean_hw(vals[0])
                if v and v not in _INVALID_MARKS:
                    return v
    except Exception:
        pass
    return ""


def _get_mac_fast() -> str:
    """用 uuid.getnode() 取 MAC"""
    try:
        mac_int = uuid.getnode()
        mac_hex = f"{mac_int:012X}"
        mac = ":".join(mac_hex[i:i+2] for i in range(0, 12, 2))
        v = _clean_hw(mac)
        return v if v and v not in _INVALID_MARKS else ""
    except Exception:
        return ""


_cached_hardware_id = None

def get_hardware_id() -> str:
    """获取硬件ID（带缓存）"""
    global _cached_hardware_id
    if _cached_hardware_id is not None:
        return _cached_hardware_id

    mg = _read_machine_guid()
    if mg:
        _cached_hardware_id = f"GUID-{mg}"
        return _cached_hardware_id

    # 优先用 MAC 地址（更快）
    mac_addr = _get_mac_fast()
    if mac_addr:
        _cached_hardware_id = f"MAC-{mac_addr}"
        return _cached_hardware_id

    # wmic 作为最后手段，缩短超时
    if platform.system().lower() == "windows":
        system_uuid = _read_wmic_single_timeout(["wmic", "csproduct", "get", "uuid"], "UUID", timeout_sec=0.3)
        if system_uuid:
            _cached_hardware_id = f"UUID-{system_uuid}"
            return _cached_hardware_id

    _cached_hardware_id = ""
    return _cached_hardware_id


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _to_base32_short(digest: bytes, length: int = 10) -> str:
    num = int.from_bytes(digest, "big")
    out = []
    while num > 0 and len(out) < 52:
        num, rem = divmod(num, 32)
        out.append(_B32_ALPHABET[rem])
    s = "".join(reversed(out)) or "A"
    return s[:length]


class AppState:
    """应用状态管理器 - 完全基于数据库存储"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppState, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._ui_config = None

    def set_ui_config(self, ui_config):
        """设置UIConfigManager实例"""
        self._ui_config = ui_config

    def get(self, key: str, default_value=None):
        """从数据库获取配置"""
        if not self._ui_config:
            raise RuntimeError("AppState未初始化，请先调用 set_ui_config()")
        return self._ui_config.get(key, default_value)

    def set(self, key: str, value):
        """保存配置到数据库"""
        if not self._ui_config:
            raise RuntimeError("AppState未初始化，请先调用 set_ui_config()")
        self._ui_config.set(key, value)

    def update(self, data_to_update: Dict):
        """批量更新配置到数据库"""
        for key, value in data_to_update.items():
            self.set(key, value)

    def ensure_identity(self) -> Tuple[bool, str]:
        """确保设备身份"""
        hw_id_now = get_hardware_id()
        if not hw_id_now:
            return False, "未能获取任何有效的硬件标识"

        uuid_ref = self.get("uuid_ref")
        device_id = self.get("device_id")

        if not uuid_ref or uuid_ref != hw_id_now or not device_id:
            rand_bytes = secrets.token_bytes(16)
            device_rand = _b64u(rand_bytes)
            digest = _sha256((hw_id_now + "|" + device_rand + "|" + APP_SALT).encode("utf-8"))
            new_device_id = _to_base32_short(digest, length=10)
            self.update({
                "uuid_ref": hw_id_now,
                "device_rand": device_rand,
                "device_id": new_device_id,
                "license_key": ""
            })
        return True, ""

    def is_activated(self) -> bool:
        """检查是否已激活"""
        license_key = self.get("license_key")
        device_id = self.get("device_id")
        if not license_key or not device_id:
            return False
        ok, _, _ = self._verify_license_internal(license_key, device_id)
        return ok

    def _verify_license_internal(self, license_str: str, device_id: str) -> Tuple[bool, str, Dict]:
        """验证许可证"""
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_public_key

            parts = (license_str or "").strip().split(".")
            if len(parts) != 2:
                return False, "许可证格式错误", {}

            p_b64, sig_b64 = parts
            payload_bytes = _b64u_dec(p_b64)
            signature = _b64u_dec(sig_b64)

            pub_key = load_pem_public_key(ED25519_PUBKEY_PEM)
            pub_key.verify(signature, payload_bytes)

            payload = json.loads(payload_bytes.decode("utf-8"))
            if str(payload.get("did", "")).strip().upper() != device_id.upper():
                return False, "设备ID不匹配", payload

            return True, "验证通过", payload
        except ImportError:
            return False, "缺少加密库 (cryptography)", {}
        except Exception as e:
            return False, f"验证失败: {e}", {}

    def verify_and_save_license(self, license_key: str) -> Tuple[bool, str]:
        """验证并保存许可证"""
        device_id = self.get("device_id")
        ok, msg, _ = self._verify_license_internal(license_key, device_id)
        if ok:
            self.update({"license_key": license_key})
        return ok, msg

    def is_auto_print_locked(self) -> bool:
        """检查自动打印是否处于锁定状态"""
        barcode_print = self.get("barcode_print", {})
        return barcode_print.get("auto_print_locked", False)

    def get_locked_code(self) -> str:
        """获取当前锁定的条码"""
        barcode_print = self.get("barcode_print", {})
        return barcode_print.get("locked_code", "")

    def lock_auto_print(self, code: str):
        """锁定自动打印并记录条码"""
        barcode_print = self.get("barcode_print", {})
        barcode_print["auto_print_locked"] = True
        barcode_print["locked_code"] = code
        self.set("barcode_print", barcode_print)

    def unlock_auto_print(self):
        """解锁自动打印"""
        barcode_print = self.get("barcode_print", {})
        barcode_print["auto_print_locked"] = False
        barcode_print["locked_code"] = None
        self.set("barcode_print", barcode_print)


# 全局单例
app_state = AppState()
