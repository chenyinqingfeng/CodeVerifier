"""
用户管理页面
"""

from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QDialog, QFormLayout, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


class UserPage(BasePage):
    """用户管理页面"""

    def __init__(self, db_manager, auth_manager, parent=None):
        self.auth_manager = auth_manager
        # 不传递ui_config，因为用户页面不需要它
        super().__init__(db_manager, None, parent)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 工具栏
        self._setup_toolbar(layout)

        # 用户列表
        self._setup_user_table(layout)

    def _setup_toolbar(self, parent_layout):
        """设置工具栏"""
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
                padding: 12px;
            }}
        """)

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setSpacing(12)

        # 新建用户按钮
        create_btn = QPushButton("+ 新建用户")
        create_btn.clicked.connect(self._show_create_dialog)
        toolbar_layout.addWidget(create_btn)

        toolbar_layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.clicked.connect(self.refresh)
        toolbar_layout.addWidget(refresh_btn)

        parent_layout.addWidget(toolbar)

    def _setup_user_table(self, parent_layout):
        """设置用户表格"""
        table_frame = QFrame()
        table_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)

        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 16, 16, 16)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels([
            "用户名", "姓名", "角色", "最后登录", "状态", "操作"
        ])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.verticalHeader().setDefaultSectionSize(44)  # 设置行高
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 只读模式

        table_layout.addWidget(self.user_table)
        parent_layout.addWidget(table_frame)

    def _show_create_dialog(self):
        """显示创建用户对话框"""
        dialog = UserDialog(self.auth_manager, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()
            self.show_message("成功", "用户创建成功", "info")

    def _load_users(self):
        """加载用户数据"""
        all_users = self.auth_manager.get_all_users()

        role_map = {'user': '操作员', 'admin': '管理员', 'developer': '开发者'}
        role_level = {'user': 1, 'admin': 2, 'developer': 3}

        # 获取当前登录用户的角色和等级
        current_user = self.auth_manager.get_current_user()
        current_role = current_user.get('role') if current_user else 'user'
        current_user_id = current_user.get('id') if current_user else None
        current_level = role_level.get(current_role, 1)

        # 根据当前用户等级过滤可见用户
        # 1级看1级，2级看1-2级，3级看1-2-3级
        users = [u for u in all_users if role_level.get(u['role'], 1) <= current_level]

        self.user_table.setRowCount(len(users))

        for row, user in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(user['username']))
            self.user_table.setItem(row, 1, QTableWidgetItem(user.get('full_name', '-')))
            self.user_table.setItem(row, 2, QTableWidgetItem(role_map.get(user['role'], user['role'])))
            self.user_table.setItem(row, 3, QTableWidgetItem(str(user.get('last_login', '-'))))

            status_text = "启用" if user['is_active'] else "禁用"
            status_item = QTableWidgetItem(status_text)
            if not user['is_active']:
                status_item.setForeground(Qt.red)
            self.user_table.setItem(row, 4, status_item)

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            # 表格内按钮样式（覆盖全局样式的padding和min-height）
            table_btn_style = "padding: 4px 8px; min-height: 0px;"

            is_self = (user['id'] == current_user_id)

            # 重置密码按钮（所有用户都可以，包括自己）
            reset_btn = QPushButton("重置密码")
            reset_btn.setFixedSize(70, 40)
            reset_btn.setStyleSheet(table_btn_style)
            # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
            reset_btn.clicked.connect(partial(self._on_reset_clicked, user['id'], user['username']))
            btn_layout.addWidget(reset_btn)

            # 禁用/启用按钮（不能操作自己）
            if not is_self:
                if user['is_active']:
                    disable_btn = QPushButton("禁用")
                    disable_btn.setFixedSize(50, 40)
                    disable_btn.setStyleSheet(table_btn_style)
                    disable_btn.clicked.connect(partial(self._on_disable_clicked, user['id']))
                    btn_layout.addWidget(disable_btn)
                else:
                    enable_btn = QPushButton("启用")
                    enable_btn.setFixedSize(50, 40)
                    enable_btn.setStyleSheet(table_btn_style)
                    enable_btn.clicked.connect(partial(self._on_enable_clicked, user['id']))
                    btn_layout.addWidget(enable_btn)

            self.user_table.setCellWidget(row, 5, btn_widget)

    def _on_reset_clicked(self, user_id: int, username: str, checked: bool = False):
        """重置密码按钮点击事件处理（兼容 Cython 编译）"""
        self._reset_password(user_id, username)

    def _on_disable_clicked(self, user_id: int, checked: bool = False):
        """禁用按钮点击事件处理（兼容 Cython 编译）"""
        self._disable_user(user_id)

    def _on_enable_clicked(self, user_id: int, checked: bool = False):
        """启用按钮点击事件处理（兼容 Cython 编译）"""
        self._enable_user(user_id)

    def _reset_password(self, user_id: int, username: str):
        """重置密码"""
        dialog = ResetPasswordDialog(username, self)
        if dialog.exec() == QDialog.Accepted:
            new_password = dialog.get_password()
            success, msg = self.auth_manager.reset_password(username, new_password)
            if success:
                self.show_message("成功", f"用户 {username} 的密码已重置", "info")
            else:
                self.show_message("错误", msg or "重置失败", "error")

    def _disable_user(self, user_id: int):
        """禁用用户"""
        if self.show_message("确认", "确定要禁用此用户吗？", "question"):
            success, msg = self.auth_manager.delete_user(user_id)
            if success:
                self.refresh()
                self.show_message("成功", "用户已禁用", "info")
            else:
                self.show_message("错误", msg or "操作失败", "error")

    def _enable_user(self, user_id: int):
        """启用用户"""
        success, msg = self.auth_manager.activate_user(user_id)
        if success:
            self.refresh()
            self.show_message("成功", "用户已启用", "info")
        else:
            self.show_message("错误", msg or "操作失败", "error")

    def refresh(self):
        """刷新页面"""
        self._load_users()


class UserDialog(QDialog):
    """用户对话框（新建）"""

    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.setWindowTitle("新建用户")
        self.setFixedSize(400, 350)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # 用户名
        self.username_input = QLineEdit()
        form_layout.addRow("用户名:", self.username_input)

        # 姓名
        self.fullname_input = QLineEdit()
        form_layout.addRow("姓名:", self.fullname_input)

        # 密码
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码:", self.password_input)

        # 确认密码
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("确认密码:", self.confirm_password_input)

        # 角色 - 根据当前用户权限动态显示可选角色
        self.role_combo = QComboBox()
        current_user = self.auth_manager.get_current_user()
        current_role = current_user.get('role') if current_user else 'user'

        # 1级只能创建1级，2级可创建1-2级，3级可创建1-2-3级
        self.role_combo.addItem("操作员", "user")
        if current_role in ('admin', 'developer'):
            self.role_combo.addItem("管理员", "admin")
        if current_role == 'developer':
            self.role_combo.addItem("开发者", "developer")

        form_layout.addRow("角色:", self.role_combo)

        layout.addLayout(form_layout)
        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("创建")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save(self):
        """保存"""
        username = self.username_input.text().strip()
        fullname = self.fullname_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        role = self.role_combo.currentData()  # 直接获取角色值

        if not username:
            QMessageBox.warning(self, "提示", "请输入用户名")
            return

        if not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "提示", "两次输入的密码不一致")
            return

        success, msg, user_id = self.auth_manager.add_user(
            username=username,
            password=password,
            full_name=fullname,
            role=role
        )

        if success:
            self.accept()
        else:
            QMessageBox.warning(self, "错误", msg or "创建失败")


class ResetPasswordDialog(QDialog):
    """重置密码对话框"""

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.setWindowTitle(f"重置密码 - {username}")
        self.setFixedSize(350, 200)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # 新密码
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("新密码:", self.password_input)

        # 确认密码
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("确认密码:", self.confirm_password_input)

        layout.addLayout(form_layout)
        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("重置")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save(self):
        """保存"""
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not password:
            QMessageBox.warning(self, "提示", "请输入新密码")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "提示", "密码长度至少6位")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "提示", "两次输入的密码不一致")
            return

        self.accept()

    def get_password(self) -> str:
        return self.password_input.text()
