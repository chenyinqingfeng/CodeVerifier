"""
UIConfigManager - UI配置管理器
负责管理所有UI相关配置，数据存储在 ui_settings 表中
版本: 3.0 (PySide6版本)
"""

import json
from typing import Any, Dict, Optional
import traceback


class UIConfigManager:
    """UI配置管理器 - 统一管理UI配置（存储在数据库中）"""

    def __init__(self, db_manager):
        self.db = db_manager

    def get(self, key: str, default: Any = None) -> Any:
        """获取单个配置值"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value, data_type FROM ui_settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row is None:
                    return default
                return self._convert_from_string(row[0], row[1])
        except Exception as e:
            print(f"[ERROR] 读取配置失败 {key}: {e}")
            return default

    def set(self, key: str, value: Any, category: str = None, data_type: str = None) -> bool:
        """设置单个配置值"""
        try:
            if data_type is None:
                data_type = self._infer_data_type(value)
            value_str = self._convert_to_string(value, data_type)

            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key FROM ui_settings WHERE key = ?", (key,))
                exists = cursor.fetchone() is not None

                if exists:
                    cursor.execute("UPDATE ui_settings SET value = ?, data_type = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
                                   (value_str, data_type, key))
                else:
                    if category is None:
                        category = 'custom'
                    cursor.execute("INSERT INTO ui_settings (key, value, category, data_type) VALUES (?, ?, ?, ?)",
                                   (key, value_str, category, data_type))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] 保存配置失败 {key}: {e}")
            return False

    def get_category(self, category: str) -> Dict[str, Any]:
        """获取某个分类下的所有配置"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, data_type FROM ui_settings WHERE category = ?", (category,))
                result = {}
                for key, value_str, data_type in cursor.fetchall():
                    simple_key = key.replace(f"{category}_", "", 1)
                    result[simple_key] = self._convert_from_string(value_str, data_type)
                return result
        except Exception as e:
            print(f"[ERROR] 读取分类配置失败 {category}: {e}")
            return {}

    def set_category(self, category: str, config_dict: Dict[str, Any]) -> bool:
        """批量设置某个分类的配置"""
        success = True
        for key, value in config_dict.items():
            full_key = f"{category}_{key}"
            if not self.set(full_key, value, category):
                success = False
        return success

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        try:
            with self.db.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, data_type FROM ui_settings")
                result = {}
                for key, value_str, data_type in cursor.fetchall():
                    result[key] = self._convert_from_string(value_str, data_type)
                return result
        except Exception as e:
            print(f"[ERROR] 读取所有配置失败: {e}")
            return {}

    # ==================== 打印配置专用方法 ====================

    def get_print_config(self) -> Dict[str, Any]:
        """获取条码打印配置"""
        config = self.get_category('print')
        config['font_name'] = 'Arial'
        return config

    def set_print_config(self, config: Dict[str, Any]) -> bool:
        """设置条码打印配置"""
        config_copy = config.copy()
        config_copy.pop('font_name', None)
        return self.set_category('print', config_copy)

    def save_print_config(self, config: Dict[str, Any]) -> bool:
        """保存条码打印配置（set_print_config的别名）"""
        return self.set_print_config(config)

    def get_scanner_config(self) -> Dict[str, Any]:
        """获取扫码器配置"""
        config = self.get_category('scanner')
        return {
            'front_port': config.get('front_port', 'COM20'),
            'back_port': config.get('back_port', 'COM21'),
            'single_mode': config.get('single_mode', False)
        }

    def set_scanner_config(self, front_port: str, back_port: str, single_mode: bool) -> bool:
        """设置扫码器配置"""
        return self.set_category('scanner', {
            'front_port': front_port,
            'back_port': back_port,
            'single_mode': single_mode
        })

    def get_plc_config(self) -> Dict[str, Any]:
        """获取PLC配置"""
        config = self.get_category('device')
        return {
            'ip': config.get('plc_ip', '192.168.0.5'),
            'port': int(config.get('plc_port', 502))
        }

    def set_plc_config(self, ip: str, port: int) -> bool:
        """设置PLC配置"""
        return self.set_category('device', {
            'plc_ip': ip,
            'plc_port': port
        })

    def get_batch_params(self) -> Dict[str, Any]:
        """获取批次生成参数"""
        config = self.get_category('batch')
        return {
            'prefix': config.get('prefix', 'STA'),
            'start': config.get('start', '01'),
            'end': config.get('end', '15'),
            'suffix': config.get('suffix', ''),
            'container_id': config.get('container_id', ''),
            'customer_id': config.get('customer_id', '')
        }

    def set_batch_params(self, **kwargs) -> bool:
        """保存批次生成参数"""
        config = {k: v for k, v in kwargs.items() if k in ['prefix', 'start', 'end', 'suffix', 'container_id', 'customer_id']}
        return self.set_category('batch', config)

    def get_batch_config(self) -> Dict[str, Any]:
        """获取批次配置"""
        return self.get_category('batch')

    def save_batch_config(self, config: Dict[str, Any]) -> bool:
        """保存批次配置"""
        return self.set_category('batch', config)

    # ==================== 语音播报配置专用方法 ====================

    def get_voice_config(self) -> Dict[str, Any]:
        """获取语音播报配置"""
        config = self.get_category('voice')
        return {
            'enabled': config.get('enabled', True),
            'rate': int(config.get('rate', 180)),
            'volume': float(config.get('volume', 1.0)),
            'repeat': int(config.get('repeat', 1))
        }

    def set_voice_config(self, enabled: bool, rate: int, volume: float = 1.0, repeat: int = 1) -> bool:
        """设置语音播报配置"""
        return self.set_category('voice', {
            'enabled': enabled,
            'rate': rate,
            'volume': volume,
            'repeat': repeat
        })

    # ==================== 打印锁定机制 ====================

    def is_print_locked(self) -> bool:
        """检查打印是否被锁定"""
        return self.get('print_auto_print_locked', False)

    def get_locked_code(self) -> Optional[str]:
        """获取当前锁定的条码"""
        locked_code = self.get('print_locked_code', '')
        return locked_code if locked_code else None

    def lock_print(self, barcode: str) -> bool:
        """锁定打印"""
        return all([
            self.set('print_auto_print_locked', True),
            self.set('print_locked_code', barcode),
            self.set('print_last_printed_code', barcode)
        ])

    def unlock_print(self) -> bool:
        """解锁打印"""
        return all([
            self.set('print_auto_print_locked', False),
            self.set('print_locked_code', '')
        ])

    # ==================== 打印匹配纠错功能 ====================

    def is_print_match_correction_enabled(self) -> bool:
        """检查打印匹配纠错功能是否启用"""
        return self.get('print_match_correction_enabled', True)  # 默认开启

    def set_print_match_correction_enabled(self, enabled: bool) -> bool:
        """设置打印匹配纠错功能开关"""
        return self.set('print_match_correction_enabled', enabled, 'print', 'bool')

    # ==================== 打印配方管理 ====================

    def get_print_recipes(self) -> list:
        """获取所有打印配方列表"""
        return self.db.get_all_print_recipes()

    def get_print_recipe_by_id(self, recipe_id: int) -> Optional[Dict]:
        """根据ID获取打印配方"""
        return self.db.get_print_recipe_by_id(recipe_id)

    def get_current_recipe_id(self) -> int:
        """获取当前使用的配方ID"""
        return self.get('print_current_recipe_id', 1)

    def set_current_recipe_id(self, recipe_id: int) -> bool:
        """设置当前使用的配方ID"""
        return self.set('print_current_recipe_id', recipe_id, 'print', 'int')

    def get_current_recipe(self) -> Optional[Dict]:
        """获取当前使用的配方"""
        recipe_id = self.get_current_recipe_id()
        return self.get_print_recipe_by_id(recipe_id)

    def create_print_recipe(self, recipe_name: str, params: Dict) -> Optional[int]:
        """创建新打印配方"""
        return self.db.create_print_recipe(recipe_name, params)

    def update_print_recipe(self, recipe_id: int, params: Dict) -> bool:
        """更新打印配方参数"""
        return self.db.update_print_recipe(recipe_id, params)

    def delete_print_recipe(self, recipe_id: int) -> bool:
        """删除打印配方"""
        return self.db.delete_print_recipe(recipe_id)

    def get_auto_print_repeat_count(self) -> int:
        """获取当前配方的自动重复打印次数"""
        recipe = self.get_current_recipe()
        if recipe:
            return recipe.get('auto_print_repeat_count', 1)
        return 1

    # ==================== 内部辅助方法 ====================

    def _convert_from_string(self, value_str: str, data_type: str) -> Any:
        """将字符串转换为指定类型"""
        try:
            if data_type == 'string':
                return value_str
            elif data_type == 'int':
                return int(value_str) if value_str else 0
            elif data_type == 'float':
                return float(value_str) if value_str else 0.0
            elif data_type == 'bool':
                return value_str.lower() in ('true', '1', 'yes')
            elif data_type == 'json':
                return json.loads(value_str) if value_str else {}
            return value_str
        except Exception:
            return value_str

    def _convert_to_string(self, value: Any, data_type: str) -> str:
        """将值转换为字符串存储"""
        try:
            if data_type == 'bool':
                return 'true' if value else 'false'
            elif data_type == 'json':
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        except Exception:
            return str(value)

    def _infer_data_type(self, value: Any) -> str:
        """自动推断数据类型"""
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        return 'string'
