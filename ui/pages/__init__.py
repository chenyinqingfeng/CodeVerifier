"""
页面组件
"""

from .base_page import BasePage
from .scan_page import ScanPage
from .batch_page import BatchPage
from .export_page import ExportPage
from .log_page import LogPage
from .device_page import DevicePage
from .customer_page import CustomerPage
from .user_page import UserPage
from .database_page import DatabasePage

__all__ = [
    'BasePage',
    'ScanPage',
    'BatchPage',
    'ExportPage',
    'LogPage',
    'DevicePage',
    'CustomerPage',
    'UserPage',
    'DatabasePage'
]
