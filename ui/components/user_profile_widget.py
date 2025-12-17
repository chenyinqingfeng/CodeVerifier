"""
用户信息显示组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

from ..styles import Colors, Fonts, Sizes


class UserProfileWidget(QWidget):
    """用户信息组件"""

    logout_clicked = Signal()  # 登出信号
    login_requested = Signal()  # 请求登录信号

    def __init__(self, auth_manager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.is_expanded = True
        self._setup_ui()
        self._apply_styles()
        self._update_user_info()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        # 用户信息容器
        self.user_container = QFrame()
        self.user_container.setObjectName("user_container")
        self.user_container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.user_container.mousePressEvent = self._on_container_click

        user_layout = QHBoxLayout(self.user_container)
        user_layout.setContentsMargins(8, 8, 8, 8)
        user_layout.setSpacing(10)

        # 头像（使用emoji图标）
        self.avatar_label = QLabel("👤")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedSize(40, 40)
        self.avatar_label.setProperty("avatar", True)
        user_layout.addWidget(self.avatar_label)

        # 用户信息（展开时显示）
        self.info_container = QWidget()
        info_layout = QVBoxLayout(self.info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.username_label = QLabel("未登录")
        self.username_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        info_layout.addWidget(self.username_label)

        self.role_label = QLabel("点击登录")
        self.role_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        self.role_label.setProperty("role", True)
        info_layout.addWidget(self.role_label)

        user_layout.addWidget(self.info_container)
        user_layout.addStretch()

        layout.addWidget(self.user_container)

        # 退出登录按钮（仅登录后显示）
        self.logout_btn = QPushButton("退出登录")
        self.logout_btn.setMinimumHeight(32)
        self.logout_btn.setProperty("logout", True)
        self.logout_btn.clicked.connect(self._on_logout)
        self.logout_btn.setVisible(False)  # 默认隐藏
        layout.addWidget(self.logout_btn)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(f"""
            #user_container {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
            }}

            #user_container:hover {{
                background-color: {Colors.SURFACE_LIGHT_2};
            }}

            QLabel[avatar="true"] {{
                background-color: {Colors.SURFACE_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 20px;
                font-size: 20px;
            }}

            QLabel {{
                color: {Colors.TEXT_PRIMARY_LIGHT};
            }}

            QLabel[role="true"] {{
                color: {Colors.TEXT_MUTED_LIGHT};
            }}

            QPushButton[logout="true"] {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Sizes.RADIUS_SM}px;
                font-size: 12px;
                padding: 4px 8px;
                min-height: 0px;
            }}

            QPushButton[logout="true"]:hover {{
                background-color: {Colors.ERROR};
                color: white;
                border-color: {Colors.ERROR};
            }}
        """)

    def _update_user_info(self):
        """更新用户信息显示"""
        user = self.auth_manager.get_current_user()

        if user:
            # 显示用户信息
            username = user.get("full_name") or user.get("username")
            role = user.get("role")

            # 设置头像图标（根据角色）
            role_icons = {
                'user': '👤',
                'admin': '👨‍💼',
                'developer': '👨‍💻'
            }
            self.avatar_label.setText(role_icons.get(role, '👤'))

            # 设置用户名
            self.username_label.setText(username)

            # 设置角色
            role_names = {'user': '操作员', 'admin': '管理员', 'developer': '开发者'}
            self.role_label.setText(role_names.get(role, '用户'))

            # 根据角色设置头像边框颜色
            role_colors = {
                'user': Colors.PRIMARY,  # 蓝色
                'admin': '#CA5010',  # 橙色
                'developer': '#107C10'  # 绿色
            }
            border_color = role_colors.get(role, Colors.PRIMARY)

            self.avatar_label.setStyleSheet(f"""
                QLabel[avatar="true"] {{
                    background-color: {Colors.SURFACE_LIGHT};
                    border: 2px solid {border_color};
                    border-radius: 20px;
                    font-size: 20px;
                }}
            """)

            # 更新角色颜色
            self.role_label.setStyleSheet(f"color: {border_color};")

            # 显示退出登录按钮
            self.logout_btn.setVisible(self.is_expanded)
        else:
            # 未登录状态
            self.avatar_label.setText("👤")
            self.username_label.setText("未登录")
            self.role_label.setText("点击登录")
            self.role_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")

            # 恢复默认头像样式
            self.avatar_label.setStyleSheet(f"""
                QLabel[avatar="true"] {{
                    background-color: {Colors.SURFACE_LIGHT};
                    border: 2px solid {Colors.BORDER};
                    border-radius: 20px;
                    font-size: 20px;
                }}
            """)

            # 隐藏退出登录按钮
            self.logout_btn.setVisible(False)

    def _on_container_click(self, event):
        """点击容器事件"""
        # 如果未登录，触发登录请求
        if not self.auth_manager.is_authenticated():
            self.login_requested.emit()

    def _on_logout(self):
        """登出"""
        self.auth_manager.logout()
        self._update_user_info()
        self.logout_clicked.emit()

    def set_expanded(self, expanded: bool):
        """设置展开/收起状态"""
        self.is_expanded = expanded
        self.info_container.setVisible(expanded)

        # 获取用户信息容器的布局
        user_layout = self.user_container.layout()

        if expanded:
            # 展开状态：左对齐，正常边距
            user_layout.setContentsMargins(8, 8, 8, 8)
            user_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.logout_btn.setText("退出登录")
        else:
            # 折叠状态：居中对齐，减小边距
            user_layout.setContentsMargins(0, 8, 0, 8)
            user_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logout_btn.setText("退出")

    def refresh(self):
        """刷新用户信息"""
        self._update_user_info()
