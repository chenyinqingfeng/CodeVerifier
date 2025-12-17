"""
UI样式常量定义 - PySide6版本
"""

from PySide6.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox
from PySide6.QtCore import Qt


class NoWheelSpinBox(QSpinBox):
    """不响应鼠标滚轮的 SpinBox"""

    def wheelEvent(self, event):
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """不响应鼠标滚轮的 DoubleSpinBox"""

    def wheelEvent(self, event):
        event.ignore()


class NoWheelComboBox(QComboBox):
    """不响应鼠标滚轮的 ComboBox"""

    def wheelEvent(self, event):
        event.ignore()


class Colors:
    """颜色定义"""
    # 主色调
    PRIMARY = "#6366f1"
    PRIMARY_HOVER = "#4f46e5"
    PRIMARY_DARK = "#3730a3"

    # 辅助色
    SECONDARY = "#ec4899"
    ACCENT = "#06b6d4"
    INFO = "#3b82f6"
    INFO_DARK = "#2563eb"
    SUCCESS = "#10b981"
    SUCCESS_DARK = "#047857"
    WARNING = "#f59e0b"
    WARNING_DARK = "#d97706"
    ERROR = "#ef4444"
    ERROR_DARK = "#dc2626"
    DANGER = "#ef4444"

    # 亮色主题
    BACKGROUND_LIGHT = "#ffffff"
    SURFACE_LIGHT = "#f3f4f6"
    SURFACE_LIGHT_2 = "#e5e7eb"
    TEXT_PRIMARY_LIGHT = "#1f2937"
    TEXT_SECONDARY_LIGHT = "#6b7280"
    TEXT_MUTED_LIGHT = "#9ca3af"

    # 暗色主题
    BACKGROUND_DARK = "#0f172a"
    SURFACE_DARK = "#1e293b"
    SURFACE_DARK_2 = "#334155"
    TEXT_PRIMARY_DARK = "#f1f5f9"
    TEXT_SECONDARY_DARK = "#cbd5e1"
    TEXT_MUTED_DARK = "#94a3b8"

    # 边框
    BORDER = "#e5e7eb"
    BORDER_DARK = "#334155"


class Fonts:
    """字体定义"""
    FAMILY = "Microsoft YaHei UI"
    FAMILY_MONO = "Consolas"

    SIZE_XS = 10
    SIZE_SM = 12
    SIZE_BASE = 14
    SIZE_LG = 16
    SIZE_XL = 18
    SIZE_2XL = 20
    SIZE_3XL = 24
    SIZE_4XL = 28


class Sizes:
    """尺寸定义"""
    # 间距
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 16
    SPACING_LG = 24
    SPACING_XL = 32

    # 圆角
    RADIUS_SM = 6
    RADIUS_MD = 8
    RADIUS_LG = 12

    # 组件尺寸
    BUTTON_HEIGHT = 40
    INPUT_HEIGHT = 40
    SIDEBAR_WIDTH = 220
    SIDEBAR_COLLAPSED = 60
    TOOLBAR_HEIGHT = 50
    STATUS_BAR_HEIGHT = 30


# 全局样式表
GLOBAL_STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 14px;
}

QMainWindow, QDialog {
    background-color: #ffffff;
}

QPushButton {
    background-color: #6366f1;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    min-height: 26px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #4f46e5;
}

QPushButton:pressed {
    background-color: #3730a3;
}

QPushButton:disabled {
    background-color: #9ca3af;
}

QPushButton[secondary="true"] {
    background-color: #f3f4f6;
    color: #1f2937;
    border: 1px solid #e5e7eb;
}

QPushButton[secondary="true"]:hover {
    background-color: #e5e7eb;
}

QPushButton[danger="true"] {
    background-color: #ef4444;
}

QPushButton[danger="true"]:hover {
    background-color: #dc2626;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #6366f1;
}

QComboBox {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px;
}

QComboBox:hover {
    border-color: #6366f1;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    gridline-color: #e5e7eb;
}

QTableWidget::item {
    padding: 8px;
}

QTableWidget::item:selected {
    background-color: #6366f1;
    color: white;
}

QHeaderView::section {
    background-color: #f3f4f6;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #f3f4f6;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #9ca3af;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #6b7280;
}

QScrollBar:horizontal {
    background-color: #f3f4f6;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #9ca3af;
    border-radius: 5px;
    min-width: 30px;
}

QLabel {
    color: #1f2937;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    color: #6366f1;
}

QTabWidget::pane {
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 2px solid #6366f1;
}

QProgressBar {
    background-color: #e5e7eb;
    border-radius: 4px;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #6366f1;
    border-radius: 4px;
}

QStatusBar {
    background-color: #f3f4f6;
    border-top: 1px solid #e5e7eb;
}

QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e7eb;
}

QMenuBar::item:selected {
    background-color: #f3f4f6;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #6366f1;
    color: white;
}
"""

# 暗色主题样式表
DARK_STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 14px;
    color: #f1f5f9;
}

QMainWindow, QDialog {
    background-color: #0f172a;
}

QPushButton {
    background-color: #6366f1;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    min-height: 26px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #4f46e5;
}

QPushButton[secondary="true"] {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
    color: #f1f5f9;
}

QLineEdit:focus, QTextEdit:focus {
    border: 2px solid #6366f1;
}

QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
    color: #f1f5f9;
}

QTableWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    gridline-color: #334155;
    color: #f1f5f9;
}

QHeaderView::section {
    background-color: #0f172a;
    border-bottom: 1px solid #334155;
}

QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #1e293b;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #475569;
}

QLabel {
    color: #f1f5f9;
}

QGroupBox {
    border: 1px solid #334155;
}

QTabWidget::pane {
    border: 1px solid #334155;
    background-color: #1e293b;
}

QTabBar::tab {
    background-color: #0f172a;
    border: 1px solid #334155;
}

QTabBar::tab:selected {
    background-color: #1e293b;
}

QStatusBar {
    background-color: #1e293b;
    border-top: 1px solid #334155;
}
"""
