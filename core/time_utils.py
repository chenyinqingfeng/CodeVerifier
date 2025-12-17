"""
时间工具函数
统一使用UTC+8（北京时间）
避免使用SQLite的CURRENT_TIMESTAMP（返回UTC时间）
"""

from datetime import datetime


def get_local_time_str() -> str:
    """
    获取本地时间字符串（UTC+8北京时间）

    Returns:
        格式化的时间字符串 "YYYY-MM-DD HH:MM:SS"
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_local_datetime() -> datetime:
    """
    获取本地时间对象（UTC+8北京时间）

    Returns:
        datetime对象
    """
    return datetime.now()
