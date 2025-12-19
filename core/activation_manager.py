"""
激活管理器 - PySide6版本
从dispenser_tester_qt提取并适配
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QMessageBox, QApplication, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .state_manager import app_state
from .security_check import check_security, SecurityGuard


class ActivationDialog(QDialog):
    """激活对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.activation_successful = False
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("软件激活")
        self.setFixedSize(600, 500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 30, 40, 30)

        # 标题
        title = QLabel("软件未激活")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 提示
        tip = QLabel("请将下方设备ID发送给授权方，以获取激活码。")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)

        # 设备ID区域
        device_id_label = QLabel("设备ID:")
        device_id_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        layout.addWidget(device_id_label)

        device_id = app_state.get("device_id", "未知")

        device_id_layout = QHBoxLayout()
        device_id_layout.setSpacing(10)

        self.device_id_text = QLineEdit(device_id)
        self.device_id_text.setReadOnly(True)
        self.device_id_text.setFont(QFont("Consolas", 12))
        self.device_id_text.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                padding: 10px 12px;
            }
        """)
        device_id_layout.addWidget(self.device_id_text, 1)

        copy_btn = QPushButton("复制")
        copy_btn.clicked.connect(self._on_copy_device_id)
        copy_btn.setMinimumWidth(80)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        device_id_layout.addWidget(copy_btn)

        layout.addLayout(device_id_layout)

        # 激活码输入区域
        license_header_layout = QHBoxLayout()
        license_label = QLabel("激活码:")
        license_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        license_header_layout.addWidget(license_label)
        license_header_layout.addStretch()

        paste_btn = QPushButton("粘贴")
        paste_btn.clicked.connect(self._on_paste_from_clipboard)
        paste_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        license_header_layout.addWidget(paste_btn)

        import_btn = QPushButton("导入文件")
        import_btn.clicked.connect(self._on_import_from_file)
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        license_header_layout.addWidget(import_btn)

        layout.addLayout(license_header_layout)

        # 激活码输入框
        self.license_input = QTextEdit()
        self.license_input.setPlaceholderText("请输入或粘贴激活码...")
        self.license_input.setFont(QFont("Consolas", 11))
        self.license_input.setMinimumHeight(120)
        self.license_input.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                padding: 10px;
            }
            QTextEdit:focus {
                border: 2px solid #6366f1;
            }
        """)
        layout.addWidget(self.license_input)

        layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        exit_btn = QPushButton("退出")
        exit_btn.setMinimumHeight(45)
        exit_btn.setMinimumWidth(120)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #333333;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        exit_btn.clicked.connect(self._on_exit)
        btn_layout.addWidget(exit_btn)

        activate_btn = QPushButton("激活")
        activate_btn.setMinimumHeight(45)
        activate_btn.setMinimumWidth(120)
        activate_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
        """)
        activate_btn.clicked.connect(self._on_activate)
        btn_layout.addWidget(activate_btn)

        layout.addLayout(btn_layout)

    def _on_copy_device_id(self):
        """复制设备ID"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.device_id_text.text())
        QMessageBox.information(self, "提示", "设备ID已复制到剪贴板")

    def _on_paste_from_clipboard(self):
        """从剪切板粘贴激活码"""
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text().strip()

        if not clipboard_text:
            QMessageBox.warning(self, "提示", "剪切板为空，请先复制激活码")
            return

        self.license_input.setPlainText(clipboard_text)
        QMessageBox.information(self, "成功", f"已从剪切板粘贴激活码\n长度: {len(clipboard_text)} 字符")

    def _on_import_from_file(self):
        """从.lic文件导入激活码"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择激活文件",
            "",
            "激活文件 (*.lic);;所有文件 (*.*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                license_content = f.read().strip()

            if not license_content:
                QMessageBox.warning(self, "错误", "激活文件为空")
                return

            self.license_input.setPlainText(license_content)
            file_name = Path(file_path).name
            QMessageBox.information(self, "导入成功", f"已从文件导入激活码\n文件: {file_name}")

        except UnicodeDecodeError:
            QMessageBox.warning(self, "错误", "文件编码错误，请确保文件为UTF-8格式")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"读取文件失败:\n{str(e)}")

    def _on_activate(self):
        """激活"""
        license_key = self.license_input.toPlainText().strip()

        if not license_key:
            QMessageBox.warning(self, "提示", "请输入激活码")
            return

        ok, msg = app_state.verify_and_save_license(license_key)

        if ok:
            self.activation_successful = True
            QMessageBox.information(self, "激活成功", "软件已成功激活！")
            self.accept()
        else:
            QMessageBox.warning(self, "激活失败", f"激活失败：{msg}")

    def _on_exit(self):
        """退出"""
        self.reject()


class ActivationManager:
    """软件激活管理器"""

    def __init__(self):
        self.activation_successful = False
        logging.info("激活管理器初始化完成")

    def run_activation_flow(self) -> bool:
        """运行软件激活流程"""
        logging.info("启动软件激活流程")

        # 安全检测：反调试、反虚拟机
        safe, reason = check_security()
        if not safe:
            # 清除设备身份信息，强制重新生成设备ID
            if reason in ("debugger", "vm"):
                from .security_check import _clear_device_identity
                _clear_device_identity()
            sys.exit(0)

        ok, error_msg = app_state.ensure_identity()
        if not ok:
            logging.error(f"设备身份标识失败: {error_msg}")
            QMessageBox.critical(None, "错误", f"无法初始化设备标识:\n{error_msg}")
            return False

        if app_state.is_activated():
            logging.info("软件已激活")
            SecurityGuard.start()  # 启动持续检测
            return True

        dialog = ActivationDialog()
        dialog.exec()

        self.activation_successful = dialog.activation_successful
        logging.info(f"激活流程结束，结果: {'成功' if self.activation_successful else '失败'}")

        if self.activation_successful:
            SecurityGuard.start()  # 启动持续检测

        return self.activation_successful

    def check_activation(self) -> bool:
        """检查激活状态"""
        ok, _ = app_state.ensure_identity()
        if not ok:
            return False
        return app_state.is_activated()
