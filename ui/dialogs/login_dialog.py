"""
登录对话框 - 角色选择版本
"""

from functools import partial

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ..styles import Colors, Fonts, Sizes


class LoginDialog(QDialog):
    """登录对话框 - 角色选择"""

    login_success = Signal(dict)  # 登录成功信号，传递用户信息

    def __init__(self, auth_manager, parent=None, required_role: str = None):
        """
        初始化登录对话框

        Args:
            auth_manager: 认证管理器
            parent: 父窗口
            required_role: 要求的最低权限等级 (user/admin/developer)
        """
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.required_role = required_role
        self.selected_role = None
        self.user_info = None

        self.setWindowTitle("选择身份")
        self.setFixedSize(420, 420)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        self.title = QLabel("选择登录身份")
        self.title.setFont(QFont(Fonts.FAMILY, 18, QFont.Bold))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        # 副标题
        self.subtitle = QLabel("点击下方按钮选择您的身份")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setProperty("subtitle", True)
        layout.addWidget(self.subtitle)

        layout.addSpacing(16)

        # 角色按钮容器
        self.role_container = QWidget()
        role_layout = QVBoxLayout(self.role_container)
        role_layout.setContentsMargins(0, 0, 0, 0)
        role_layout.setSpacing(10)

        # 操作员（用户名是 operator01）
        self.operator_btn = QPushButton("👤  操作员")
        self.operator_btn.setMinimumHeight(50)
        self.operator_btn.setProperty("role_button", True)
        self.operator_btn.setProperty("role", "operator")
        # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
        self.operator_btn.clicked.connect(partial(self._handle_role_click, "user", "operator01"))
        role_layout.addWidget(self.operator_btn)

        # 管理员
        self.admin_btn = QPushButton("👨‍💼  管理员")
        self.admin_btn.setMinimumHeight(50)
        self.admin_btn.setProperty("role_button", True)
        self.admin_btn.setProperty("role", "admin")
        self.admin_btn.clicked.connect(partial(self._handle_role_click, "admin", "admin"))
        role_layout.addWidget(self.admin_btn)

        # 开发者
        self.developer_btn = QPushButton("👨‍💻  开发者")
        self.developer_btn.setMinimumHeight(50)
        self.developer_btn.setProperty("role_button", True)
        self.developer_btn.setProperty("role", "developer")
        self.developer_btn.clicked.connect(partial(self._handle_role_click, "developer", "developer"))
        role_layout.addWidget(self.developer_btn)

        layout.addWidget(self.role_container)

        # 密码输入容器（初始隐藏）
        self.password_container = QWidget()
        password_layout = QVBoxLayout(self.password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(12)

        password_layout.addStretch()

        password_label = QLabel("请输入密码")
        password_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        password_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._on_login)
        password_layout.addWidget(self.password_input)

        # 错误提示
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color: {Colors.ERROR};")
        self.error_label.setVisible(False)
        password_layout.addWidget(self.error_label)

        password_layout.addStretch()

        # 登录和返回按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.back_btn = QPushButton("返回")
        self.back_btn.setMinimumHeight(40)
        self.back_btn.setProperty("secondary", True)
        self.back_btn.clicked.connect(self._on_back)
        button_layout.addWidget(self.back_btn)

        self.login_btn = QPushButton("登录")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.clicked.connect(self._on_login)
        button_layout.addWidget(self.login_btn)

        password_layout.addLayout(button_layout)

        self.password_container.setVisible(False)
        layout.addWidget(self.password_container, 1)  # 给予拉伸权重

        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setProperty("secondary", True)
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BACKGROUND_LIGHT};
            }}

            QLabel {{
                color: {Colors.TEXT_PRIMARY_LIGHT};
            }}

            QLabel[subtitle="true"] {{
                color: {Colors.TEXT_SECONDARY_LIGHT};
                font-size: 13px;
            }}

            QLineEdit {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Sizes.RADIUS_MD}px;
                padding: 10px 12px;
                font-size: 14px;
            }}

            QLineEdit:focus {{
                border: 2px solid {Colors.PRIMARY};
                padding: 9px 11px;
            }}

            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}

            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_DARK};
            }}

            QPushButton[secondary="true"] {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: 1px solid {Colors.BORDER};
            }}

            QPushButton[secondary="true"]:hover {{
                background-color: {Colors.SURFACE_LIGHT_2};
            }}

            QPushButton[role_button="true"] {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: 2px solid {Colors.BORDER};
                font-size: 15px;
                font-weight: bold;
                text-align: left;
                padding: 12px 20px;
            }}

            QPushButton[role_button="true"]:hover {{
                background-color: {Colors.PRIMARY};
                color: white;
                border-color: {Colors.PRIMARY};
            }}

            QPushButton[role="admin"]:hover {{
                background-color: #CA5010;
                border-color: #CA5010;
            }}

            QPushButton[role="developer"]:hover {{
                background-color: #107C10;
                border-color: #107C10;
            }}
        """)

    def _handle_role_click(self, role: str, username: str, checked: bool = False):
        """角色按钮点击事件处理（兼容 Cython 编译）"""
        self._on_role_select(role, username)

    def _on_role_select(self, role: str, username: str):
        """角色选择"""
        self.selected_role = role
        self.selected_username = username

        # 更新标题
        role_names = {'user': '操作员', 'admin': '管理员', 'developer': '开发者'}
        role_name = role_names.get(role, '用户')
        self.title.setText(f"{role_name}登录")
        self.subtitle.setText(f"请输入{role_name}密码")

        # 隐藏角色选择，显示密码输入
        self.role_container.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.password_container.setVisible(True)

        # 清空并聚焦密码输入框
        self.password_input.clear()
        self.error_label.setVisible(False)
        self.password_input.setFocus()

    def _on_back(self):
        """返回角色选择"""
        self.selected_role = None
        self.selected_username = None

        # 恢复标题
        self.title.setText("选择登录身份")
        self.subtitle.setText("点击下方按钮选择您的身份")

        # 显示角色选择，隐藏密码输入
        self.role_container.setVisible(True)
        self.cancel_btn.setVisible(True)
        self.password_container.setVisible(False)

        # 清空密码和错误
        self.password_input.clear()
        self.error_label.setVisible(False)

    def _on_login(self):
        """登录"""
        if not self.selected_role:
            return

        password = self.password_input.text()
        if not password:
            self._show_error("请输入密码")
            return

        # 执行登录
        success, message = self.auth_manager.login(self.selected_username, password)

        if success:
            # 检查权限是否满足要求
            if self.required_role:
                if not self.auth_manager.has_permission(self.required_role):
                    role_names = {'user': '操作员', 'admin': '管理员', 'developer': '开发者'}
                    required_name = role_names.get(self.required_role, self.required_role)
                    self._show_error(f"需要{required_name}或更高权限")
                    self.auth_manager.logout()  # 退出登录
                    return

            self.user_info = self.auth_manager.get_current_user()
            self.login_success.emit(self.user_info)
            self.accept()
        else:
            self._show_error(message or "用户名或密码错误")
            self.password_input.clear()
            self.password_input.setFocus()

    def _show_error(self, message: str):
        """显示错误信息"""
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def get_user_info(self) -> dict:
        """获取登录用户信息"""
        return self.user_info
