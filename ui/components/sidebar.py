"""
侧边栏导航组件 - PySide6版本
"""

from functools import partial
from typing import Optional, Dict
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ..styles import Colors, Fonts, Sizes
from .user_profile_widget import UserProfileWidget


class NavItem:
    """导航项"""
    def __init__(self, id: str, text: str, icon: str = "", page: str = None, required_role: str = None):
        """
        初始化导航项

        Args:
            id: 导航项ID
            text: 显示文本
            icon: 图标
            page: 对应页面ID
            required_role: 需要的最低权限等级 (user/admin/developer)
        """
        self.id = id
        self.text = text
        self.icon = icon
        self.page = page or id
        self.required_role = required_role
        self.button: Optional[QPushButton] = None
        self.is_active = False


class Sidebar(QFrame):
    """侧边栏导航"""

    # 常量定义
    WIDTH_EXPANDED = 220
    WIDTH_COLLAPSED = 60
    NAV_BTN_HEIGHT = 44
    ICON_FONT_SIZE = 18

    page_changed = Signal(str)
    login_requested = Signal(str)
    logout_clicked = Signal()

    def __init__(self, parent=None, controller=None, auth_manager=None):
        super().__init__(parent)
        self.controller = controller
        self.auth_manager = auth_manager
        self.nav_items: Dict[str, NavItem] = {}
        self.active_page = None
        self.is_collapsed = False
        self.user_profile = None
        self._pending_nav_id = None

        self._setup_ui()

    def _setup_ui(self):
        """初始化UI"""
        self.setObjectName("sidebar")
        self.setFixedWidth(self.WIDTH_EXPANDED)
        self.setStyleSheet(f"""
            #sidebar {{
                background-color: {Colors.SURFACE_LIGHT};
                border-right: 1px solid {Colors.BORDER};
            }}
        """)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # === 头部区域 ===
        self._create_header(main_layout)

        # === 导航区域 ===
        self.nav_container = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(4)
        main_layout.addWidget(self.nav_container)

        # 弹性空间
        main_layout.addStretch()

        # === 底部用户区域 ===
        self._create_footer(main_layout)

    def _create_header(self, parent_layout):
        """创建头部"""
        self.header = QFrame()
        self.header.setFixedHeight(50)
        self.header.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 0, 8, 0)
        header_layout.setSpacing(8)

        # Logo文字
        self.logo_label = QLabel("扫码系统")
        self.logo_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        self.logo_label.setStyleSheet(f"color: {Colors.PRIMARY};")
        header_layout.addWidget(self.logo_label)

        header_layout.addStretch()

        # 折叠按钮 - 用大号三角符号
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedSize(44, 44)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setToolTip("收起侧边栏")
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 10px;
                color: {Colors.TEXT_PRIMARY_LIGHT};
                font-size: 36px;
            }}
            QPushButton:hover {{
                background-color: {Colors.SURFACE_LIGHT_2};
                color: {Colors.PRIMARY};
            }}
        """)
        self.toggle_btn.clicked.connect(self._toggle_sidebar)
        header_layout.addWidget(self.toggle_btn)

        parent_layout.addWidget(self.header)

    def _create_footer(self, parent_layout):
        """创建底部用户区域"""
        if self.auth_manager:
            self.user_profile = UserProfileWidget(self.auth_manager, self)
            self.user_profile.login_requested.connect(self._on_login_requested)
            self.user_profile.logout_clicked.connect(self._on_logout)
            parent_layout.addWidget(self.user_profile)
        else:
            self._create_simple_footer(parent_layout)

    def _create_simple_footer(self, parent_layout):
        """创建简单的底部（无auth_manager时）"""
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 8, 10, 8)

        # 头像
        self.avatar_btn = QPushButton("U")
        self.avatar_btn.setFixedSize(36, 36)
        self.avatar_btn.setFont(QFont(Fonts.FAMILY, 14, QFont.Bold))
        self.avatar_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 18px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        self.avatar_btn.clicked.connect(self._on_avatar_click)
        footer_layout.addWidget(self.avatar_btn)

        # 用户信息容器
        self.user_info_widget = QWidget()
        info_layout = QVBoxLayout(self.user_info_widget)
        info_layout.setContentsMargins(8, 0, 0, 0)
        info_layout.setSpacing(2)

        self.user_name_label = QLabel("操作员")
        self.user_name_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.user_name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        info_layout.addWidget(self.user_name_label)

        self.user_status_label = QLabel("未登录")
        self.user_status_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        self.user_status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        info_layout.addWidget(self.user_status_label)

        footer_layout.addWidget(self.user_info_widget)
        footer_layout.addStretch()

        parent_layout.addWidget(footer)

    # ==================== 导航项管理 ====================

    def add_nav_item(self, nav_item: NavItem):
        """添加导航项"""
        self.nav_items[nav_item.id] = nav_item

        btn = QPushButton()
        btn.setFixedHeight(self.NAV_BTN_HEIGHT)
        btn.setCursor(Qt.PointingHandCursor)
        # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
        btn.clicked.connect(partial(self._handle_nav_click, nav_item.id))

        nav_item.button = btn
        self._update_nav_button(nav_item, self.is_collapsed)
        self.nav_layout.addWidget(btn)

    def add_separator(self, text: str = ""):
        """添加分隔符"""
        if text:
            label = QLabel(text)
            label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
            label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT}; padding: 8px 12px;")
            self.nav_layout.addWidget(label)

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {Colors.BORDER};")
        self.nav_layout.addWidget(separator)

    def _update_nav_button(self, nav_item: NavItem, collapsed: bool):
        """更新导航按钮的显示"""
        btn = nav_item.button
        if not btn:
            return

        if collapsed:
            # 折叠状态：只显示图标，居中
            btn.setText(nav_item.icon)
            btn.setFont(QFont(Fonts.FAMILY, self.ICON_FONT_SIZE))
            btn.setStyleSheet(self._get_collapsed_style(nav_item.is_active))
        else:
            # 展开状态：显示图标+文字
            btn.setText(f"  {nav_item.icon}   {nav_item.text}")
            btn.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
            btn.setStyleSheet(self._get_expanded_style(nav_item.is_active))

    def _get_expanded_style(self, is_active: bool) -> str:
        """展开状态样式"""
        if is_active:
            return f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Sizes.RADIUS_MD}px;
                    text-align: left;
                    padding-left: 8px;
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                text-align: left;
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background-color: {Colors.SURFACE_LIGHT_2};
            }}
        """

    def _get_collapsed_style(self, is_active: bool) -> str:
        """折叠状态样式"""
        if is_active:
            return f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Sizes.RADIUS_MD}px;
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
            }}
            QPushButton:hover {{
                background-color: {Colors.SURFACE_LIGHT_2};
            }}
        """

    # ==================== 折叠/展开 ====================

    def _toggle_sidebar(self):
        """切换侧边栏折叠状态"""
        self.is_collapsed = not self.is_collapsed

        if self.is_collapsed:
            self._collapse()
        else:
            self._expand()

    def _collapse(self):
        """折叠侧边栏"""
        self.setFixedWidth(self.WIDTH_COLLAPSED)

        # 头部 - 去掉背景，去掉边距，让按钮直接显示
        self.header.setStyleSheet("QFrame { background-color: transparent; border: none; }")
        self.header.layout().setContentsMargins(0, 0, 0, 0)
        self.logo_label.hide()
        self.toggle_btn.setText("▶")
        self.toggle_btn.setToolTip("展开侧边栏")

        # 更新所有导航按钮
        for item in self.nav_items.values():
            self._update_nav_button(item, True)

        # 用户信息
        if self.user_profile:
            self.user_profile.set_expanded(False)
        elif hasattr(self, 'user_info_widget'):
            self.user_info_widget.hide()

    def _expand(self):
        """展开侧边栏"""
        self.setFixedWidth(self.WIDTH_EXPANDED)

        # 头部 - 恢复背景和边距
        self.header.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)
        self.header.layout().setContentsMargins(12, 0, 8, 0)
        self.logo_label.show()
        self.toggle_btn.setText("◀")
        self.toggle_btn.setToolTip("收起侧边栏")

        # 更新所有导航按钮
        for item in self.nav_items.values():
            self._update_nav_button(item, False)

        # 用户信息
        if self.user_profile:
            self.user_profile.set_expanded(True)
        elif hasattr(self, 'user_info_widget'):
            self.user_info_widget.show()

    # ==================== 导航逻辑 ====================

    def _handle_nav_click(self, nav_id: str, checked: bool = False):
        """导航按钮点击事件处理（兼容 Cython 编译）"""
        self._on_nav_click(nav_id)

    def _on_nav_click(self, nav_id: str):
        """导航项点击"""
        nav_item = self.nav_items.get(nav_id)
        if not nav_item:
            return

        # 检查权限
        if nav_item.required_role and self.auth_manager:
            if not self.auth_manager.has_permission(nav_item.required_role):
                self._pending_nav_id = nav_id
                self.login_requested.emit(nav_item.required_role)
                return

        self._navigate_to(nav_id)

    def _navigate_to(self, nav_id: str):
        """导航到指定页面"""
        nav_item = self.nav_items.get(nav_id)
        if not nav_item:
            return

        self.set_active_page(nav_id)
        self.page_changed.emit(nav_item.page)

        if self.controller and hasattr(self.controller, 'show_page'):
            self.controller.show_page(nav_item.page)

    def set_active_page(self, nav_id: str):
        """设置活动页面"""
        for item in self.nav_items.values():
            item.is_active = (item.id == nav_id)
            self._update_nav_button(item, self.is_collapsed)

        self.active_page = nav_id

    def try_pending_navigation(self):
        """尝试执行待跳转的导航（登录成功后调用）"""
        if self._pending_nav_id:
            nav_id = self._pending_nav_id
            self._pending_nav_id = None

            nav_item = self.nav_items.get(nav_id)
            if nav_item and nav_item.required_role and self.auth_manager:
                if self.auth_manager.has_permission(nav_item.required_role):
                    self._navigate_to(nav_id)

    # ==================== 用户信息 ====================

    def set_auth_manager(self, auth_manager):
        """设置认证管理器"""
        self.auth_manager = auth_manager

        if self.user_profile:
            self.user_profile.setParent(None)
            self.user_profile.deleteLater()

        self.user_profile = UserProfileWidget(self.auth_manager, self)
        self.user_profile.login_requested.connect(self._on_login_requested)
        self.user_profile.logout_clicked.connect(self._on_logout)

        self.layout().addWidget(self.user_profile)

        if self.is_collapsed:
            self.user_profile.set_expanded(False)

    def _on_avatar_click(self):
        """头像点击"""
        if self.controller and hasattr(self.controller, 'show_login_dialog'):
            self.controller.show_login_dialog()

    def _on_login_requested(self):
        """登录请求"""
        self.login_requested.emit("")

    def _on_logout(self):
        """登出"""
        self.logout_clicked.emit()

    def update_user_info(self, username: str = "操作员", role: str = "user"):
        """更新用户信息"""
        if self.user_profile:
            self.user_profile.refresh()
        else:
            role_text = {'user': '操作员', 'admin': '管理员', 'developer': '开发者'}.get(role, '操作员')
            if hasattr(self, 'user_name_label'):
                self.user_name_label.setText(username)
            if hasattr(self, 'user_status_label'):
                self.user_status_label.setText(role_text)
                self.user_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")

    def refresh_user_info(self):
        """刷新用户信息"""
        if self.user_profile:
            self.user_profile.refresh()
