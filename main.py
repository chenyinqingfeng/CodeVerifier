"""
扫码验证系统 - 主入口
"""

import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from core.state_manager import app_state
from core.database_manager import DatabaseManager
from core.ui_config_manager import UIConfigManager
from core.activation_manager import ActivationManager
from ui.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("扫码验证系统")
    app.setApplicationVersion("3.0.0")
    app.setOrganizationName("")

    default_font = QFont("Microsoft YaHei UI", 10)
    app.setFont(default_font)

    db_manager = DatabaseManager()
    ui_config = UIConfigManager(db_manager)
    app_state.set_ui_config(ui_config)

    activation_manager = ActivationManager()
    if not activation_manager.run_activation_flow():
        sys.exit(0)

    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
