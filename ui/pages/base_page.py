"""
基础页面类 - 所有页面的父类
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..styles import Colors, Fonts, Sizes


class BasePage(QWidget):
    """基础页面类"""

    def __init__(self, db_manager, ui_config, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.ui_config = ui_config
        self.main_window = parent

        self._setup_ui()

    def _setup_ui(self):
        """子类需要重写此方法"""
        pass

    def refresh(self):
        """刷新页面数据，子类可重写"""
        pass

    def show_message(self, title: str, message: str, msg_type: str = "info"):
        """显示消息

        msg_type:
            - info: 信息提示（OK按钮）
            - warning: 警告确认（Yes/No按钮，返回bool）
            - critical: 危险确认（Yes/No按钮，返回bool）
            - error: 错误提示（OK按钮）
            - question: 询问确认（Yes/No按钮，返回bool）
        """
        from PySide6.QtWidgets import QMessageBox
        if msg_type == "info":
            QMessageBox.information(self, title, message)
            return True
        elif msg_type == "warning":
            # 警告确认，带Yes/No按钮
            return QMessageBox.warning(self, title, message,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes
        elif msg_type == "critical":
            # 危险确认，带Yes/No按钮
            return QMessageBox.critical(self, title, message,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes
        elif msg_type == "error":
            QMessageBox.critical(self, title, message)
            return False
        elif msg_type == "question":
            return QMessageBox.question(self, title, message,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes
        return False

    def set_status(self, message: str):
        """设置状态栏消息"""
        if self.main_window and hasattr(self.main_window, 'set_status'):
            self.main_window.set_status(message)
