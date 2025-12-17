"""
主窗口 - PySide6版本
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from .styles import GLOBAL_STYLESHEET, Colors, Fonts, Sizes
from .components.sidebar import Sidebar, NavItem
from .pages.scan_page import ScanPage
from .pages.batch_page import BatchPage
from .pages.print_page import PrintPage
from .pages.export_page import ExportPage
from .pages.log_page import LogPage
from .pages.device_page import DevicePage
from .pages.customer_page import CustomerPage
from .pages.user_page import UserPage
from .pages.database_page import DatabasePage
from .pages.changelog_page import ChangelogPage

from core.database_manager import DatabaseManager
from core.ui_config_manager import UIConfigManager
from core.auth_manager import AuthManager
from core.scan_controller import ScanController


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("条码验证系统")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # 应用全局样式
        self.setStyleSheet(GLOBAL_STYLESHEET)

        # 初始化管理器
        self.db_manager = DatabaseManager()
        self.ui_config = UIConfigManager(self.db_manager)
        self.auth_manager = AuthManager(self.db_manager)

        # 初始化扫码控制器
        self.scan_controller = ScanController(self.db_manager, self.ui_config)
        self._setup_scan_controller_signals()

        self.current_user = None
        self.pages = {}

        # 自动登出定时器（10分钟）
        self._auto_logout_timer = QTimer()
        self._auto_logout_timer.setSingleShot(True)
        self._auto_logout_timer.timeout.connect(self._on_auto_logout)

        self._setup_ui()
        self._setup_navigation()
        self._center_window()

        # 初始化锁定状态显示
        self._on_print_lock_changed(False, "")

    def _setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏（传入 auth_manager）
        self.sidebar = Sidebar(self, controller=self, auth_manager=self.auth_manager)
        self.sidebar.login_requested.connect(self._on_login_requested)
        self.sidebar.logout_clicked.connect(self._on_logout)
        main_layout.addWidget(self.sidebar)

        # 右侧内容区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 顶部栏
        self._setup_topbar(right_layout)

        # 页面堆栈
        self.page_stack = QStackedWidget()
        right_layout.addWidget(self.page_stack)

        # 状态栏
        self._setup_statusbar(right_layout)

        main_layout.addWidget(right_widget)

    def _setup_topbar(self, parent_layout):
        """设置顶部栏"""
        topbar = QFrame()
        topbar.setFixedHeight(Sizes.TOOLBAR_HEIGHT)
        topbar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)

        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(16, 0, 16, 0)

        # 面包屑
        self.breadcrumb_label = QLabel("首页")
        self.breadcrumb_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        self.breadcrumb_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        topbar_layout.addWidget(self.breadcrumb_label)

        # 扫码状态显示区域（只在扫码验证页面显示）
        self._setup_scan_status(topbar_layout)

        # 批次统计显示区域（只在批次管理页面显示）
        self._setup_batch_stats(topbar_layout)

        topbar_layout.addStretch()

        # 设备状态指示灯
        self._setup_device_indicators(topbar_layout)

        parent_layout.addWidget(topbar)

    def _setup_scan_status(self, parent_layout):
        """设置扫码状态显示"""
        self.scan_status_frame = QFrame()
        scan_layout = QHBoxLayout(self.scan_status_frame)
        scan_layout.setContentsMargins(30, 0, 0, 0)
        scan_layout.setSpacing(20)

        # 正面扫码状态
        front_label = QLabel("正面:")
        front_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        front_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        scan_layout.addWidget(front_label)

        self.front_scan_status = QLabel("等待扫码")
        self.front_scan_status.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.front_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        scan_layout.addWidget(self.front_scan_status)

        # 反面扫码状态
        back_label = QLabel("反面:")
        back_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        back_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        scan_layout.addWidget(back_label)

        self.back_scan_status = QLabel("等待扫码")
        self.back_scan_status.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.back_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        scan_layout.addWidget(self.back_scan_status)

        # 打印锁定状态（在结果前面显示）
        lock_label = QLabel("锁定:")
        lock_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        lock_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        lock_label.hide()
        scan_layout.addWidget(lock_label)
        self._lock_title_label = lock_label  # 保存引用

        self.print_lock_label = QLabel("未锁定")
        self.print_lock_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.print_lock_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        self.print_lock_label.hide()  # 默认隐藏，功能启用时显示
        scan_layout.addWidget(self.print_lock_label)

        # 结果状态
        result_label = QLabel("结果:")
        result_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        result_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        scan_layout.addWidget(result_label)

        self.result_scan_status = QLabel("等待扫码")
        self.result_scan_status.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.result_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        scan_layout.addWidget(self.result_scan_status)

        parent_layout.addWidget(self.scan_status_frame)

    def _setup_batch_stats(self, parent_layout):
        """设置批次统计显示"""
        self.batch_stats_frame = QFrame()
        stats_layout = QHBoxLayout(self.batch_stats_frame)
        stats_layout.setContentsMargins(30, 0, 0, 0)
        stats_layout.setSpacing(15)

        # 全部
        all_label = QLabel("全部:")
        all_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        all_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        stats_layout.addWidget(all_label)

        self.batch_all_count = QLabel("0")
        self.batch_all_count.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        self.batch_all_count.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        stats_layout.addWidget(self.batch_all_count)

        # 待激活
        pending_label = QLabel("待激活:")
        pending_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        pending_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        stats_layout.addWidget(pending_label)

        self.batch_pending_count = QLabel("0")
        self.batch_pending_count.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        self.batch_pending_count.setStyleSheet(f"color: {Colors.WARNING};")
        stats_layout.addWidget(self.batch_pending_count)

        # 活动中
        active_label = QLabel("活动中:")
        active_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        active_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        stats_layout.addWidget(active_label)

        self.batch_active_count = QLabel("0")
        self.batch_active_count.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        self.batch_active_count.setStyleSheet(f"color: {Colors.SUCCESS};")
        stats_layout.addWidget(self.batch_active_count)

        # 已归档
        archived_label = QLabel("已归档:")
        archived_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        archived_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        stats_layout.addWidget(archived_label)

        self.batch_archived_count = QLabel("0")
        self.batch_archived_count.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        self.batch_archived_count.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        stats_layout.addWidget(self.batch_archived_count)

        self.batch_stats_frame.hide()  # 默认隐藏
        parent_layout.addWidget(self.batch_stats_frame)

    def _update_batch_stats(self):
        """更新批次统计信息"""
        try:
            # 查询各状态批次数量
            result = self.db_manager.execute_query("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) as archived
                FROM batches
            """)
            if result:
                total, pending, active, archived = result[0]
                self.batch_all_count.setText(str(total or 0))
                self.batch_pending_count.setText(str(pending or 0))
                self.batch_active_count.setText(str(active or 0))
                self.batch_archived_count.setText(str(archived or 0))
        except Exception as e:
            print(f"[ERROR] 更新批次统计失败: {e}")

    def _setup_device_indicators(self, parent_layout):
        """设置设备状态指示灯"""
        # PLC状态
        plc_frame = QFrame()
        plc_layout = QHBoxLayout(plc_frame)
        plc_layout.setContentsMargins(8, 0, 8, 0)
        plc_layout.setSpacing(4)

        plc_label = QLabel("PLC")
        plc_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        plc_layout.addWidget(plc_label)

        self.plc_indicator = QLabel("●")
        self.plc_indicator.setStyleSheet(f"color: {Colors.ERROR};")
        plc_layout.addWidget(self.plc_indicator)

        parent_layout.addWidget(plc_frame)

        # 正面扫码枪状态
        front_frame = QFrame()
        front_layout = QHBoxLayout(front_frame)
        front_layout.setContentsMargins(8, 0, 8, 0)
        front_layout.setSpacing(4)

        front_label = QLabel("正面")
        front_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        front_layout.addWidget(front_label)

        self.front_indicator = QLabel("●")
        self.front_indicator.setStyleSheet(f"color: {Colors.ERROR};")
        front_layout.addWidget(self.front_indicator)

        parent_layout.addWidget(front_frame)

        # 反面扫码枪状态
        back_frame = QFrame()
        back_layout = QHBoxLayout(back_frame)
        back_layout.setContentsMargins(8, 0, 8, 0)
        back_layout.setSpacing(4)

        back_label = QLabel("反面")
        back_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        back_layout.addWidget(back_label)

        self.back_indicator = QLabel("●")
        self.back_indicator.setStyleSheet(f"color: {Colors.ERROR};")
        back_layout.addWidget(self.back_indicator)

        parent_layout.addWidget(back_frame)

        # 打印机状态
        printer_frame = QFrame()
        printer_layout = QHBoxLayout(printer_frame)
        printer_layout.setContentsMargins(8, 0, 8, 0)
        printer_layout.setSpacing(4)

        printer_label = QLabel("打印机")
        printer_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        printer_layout.addWidget(printer_label)

        self.printer_indicator = QLabel("●")
        self.printer_indicator.setStyleSheet(f"color: {Colors.ERROR};")
        printer_layout.addWidget(self.printer_indicator)

        parent_layout.addWidget(printer_frame)

    def _setup_statusbar(self, parent_layout):
        """设置状态栏"""
        statusbar = QFrame()
        statusbar.setFixedHeight(Sizes.STATUS_BAR_HEIGHT)
        statusbar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-top: 1px solid {Colors.BORDER};
            }}
        """)

        statusbar_layout = QHBoxLayout(statusbar)
        statusbar_layout.setContentsMargins(16, 0, 16, 0)

        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        statusbar_layout.addWidget(self.status_label)

        statusbar_layout.addStretch()

        version_label = QLabel("V3.6")
        version_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        version_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        statusbar_layout.addWidget(version_label)

        parent_layout.addWidget(statusbar)

    def _setup_navigation(self):
        """设置导航"""
        # 添加导航项
        nav_items = [
            NavItem("scan", "扫码验证", "📷", "scan"),
            NavItem("batch", "批次管理", "📦", "batch"),
            NavItem("print", "条码打印", "🖨", "print"),
            NavItem("export", "数据导出", "📊", "export"),
            NavItem("log", "日志查看", "📋", "log"),
            NavItem("changelog", "更新日志", "📝", "changelog"),
        ]

        for item in nav_items:
            self.sidebar.add_nav_item(item)

        self.sidebar.add_separator("管理功能")

        # 管理页面需要权限：
        # - 设备连接、客户管理: 需要admin(2级)权限
        # - 用户管理: 需要user(1级)权限，内部动态控制可见范围
        # - 数据库管理: 需要developer(3级)权限
        system_items = [
            NavItem("device", "设备连接", "🔌", "device", required_role="admin"),
            NavItem("customer", "客户管理", "🏢", "customer", required_role="admin"),
            NavItem("user", "用户管理", "👤", "user", required_role="user"),
            NavItem("database", "数据库管理", "💾", "database", required_role="developer"),
        ]

        for item in system_items:
            self.sidebar.add_nav_item(item)

        # 创建页面
        self._create_pages()

        # 默认显示扫码验证页面
        self.sidebar.set_active_page("scan")
        self.show_page("scan")

    def _create_pages(self):
        """创建所有页面"""
        self.pages["scan"] = ScanPage(self.db_manager, self.ui_config, self)
        self.pages["batch"] = BatchPage(self.db_manager, self.ui_config, self)
        self.pages["print"] = PrintPage(self.db_manager, self.ui_config, self)
        self.pages["export"] = ExportPage(self.db_manager, self.ui_config, self)
        self.pages["log"] = LogPage(self.db_manager, self.ui_config, self)
        self.pages["changelog"] = ChangelogPage(self.db_manager, self.ui_config, self)
        self.pages["device"] = DevicePage(self.db_manager, self.ui_config, self)
        self.pages["customer"] = CustomerPage(self.db_manager, self.ui_config, self)
        self.pages["user"] = UserPage(self.db_manager, self.auth_manager, self)
        self.pages["database"] = DatabasePage(self.db_manager, self.ui_config, self)

        for page in self.pages.values():
            self.page_stack.addWidget(page)

    def show_page(self, page_id: str):
        """显示指定页面"""
        page = self.pages.get(page_id)
        if page:
            self.page_stack.setCurrentWidget(page)

            # 更新面包屑
            page_names = {
                "scan": "扫码验证",
                "batch": "批次管理",
                "print": "条码打印",
                "export": "数据导出",
                "log": "日志查看",
                "changelog": "更新日志",
                "device": "设备连接",
                "customer": "客户管理",
                "user": "用户管理",
                "database": "数据库管理"
            }
            self.breadcrumb_label.setText(page_names.get(page_id, "首页"))

            # 扫码状态只在扫码验证页面显示
            self.scan_status_frame.setVisible(page_id == "scan")

            # 批次统计只在批次管理页面显示
            self.batch_stats_frame.setVisible(page_id == "batch")
            if page_id == "batch":
                self._update_batch_stats()

            # 刷新页面
            if hasattr(page, 'refresh'):
                page.refresh()

    def show_login_dialog(self, required_role: str = None):
        """显示登录对话框"""
        from .dialogs.login_dialog import LoginDialog
        dialog = LoginDialog(self.auth_manager, self, required_role=required_role)
        if dialog.exec():
            user_info = dialog.get_user_info()
            if user_info:
                self.current_user = user_info
                self.sidebar.refresh_user_info()
                self.set_status(f"欢迎, {user_info.get('full_name', user_info.get('username', ''))}")

                # 2级及以上权限启动10分钟自动登出
                if self.auth_manager.has_permission('admin'):
                    self._start_auto_logout_timer()

                return True
        return False

    def _start_auto_logout_timer(self):
        """启动自动登出定时器（10分钟）"""
        self._auto_logout_timer.stop()
        self._auto_logout_timer.start(10 * 60 * 1000)  # 10分钟

    def _on_auto_logout(self):
        """自动登出回调"""
        if self.auth_manager.is_authenticated():
            self.auth_manager.logout()
            self.current_user = None
            self.sidebar.refresh_user_info()
            self.set_status("登录已超时，已自动退出")

    def _on_login_requested(self, required_role: str):
        """处理登录请求"""
        # 弹出登录对话框
        if self.show_login_dialog(required_role if required_role else None):
            # 登录成功后，尝试执行待跳转的导航
            self.sidebar.try_pending_navigation()

    def _on_logout(self):
        """处理登出"""
        self._auto_logout_timer.stop()  # 停止自动登出定时器
        self.auth_manager.logout()
        self.current_user = None
        self.sidebar.refresh_user_info()
        self.set_status("已退出登录")

    def set_status(self, message: str):
        """设置状态栏消息"""
        self.status_label.setText(message)

    def update_device_status(self, device: str, connected: bool):
        """更新设备状态"""
        color = Colors.SUCCESS if connected else Colors.ERROR
        if device == "plc":
            self.plc_indicator.setStyleSheet(f"color: {color};")
        elif device == "front":
            self.front_indicator.setStyleSheet(f"color: {color};")
        elif device == "back":
            self.back_indicator.setStyleSheet(f"color: {color};")
        elif device == "printer":
            self.printer_indicator.setStyleSheet(f"color: {color};")

    def _center_window(self):
        """居中显示窗口"""
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _setup_scan_controller_signals(self):
        """设置扫码控制器信号连接"""
        # 设备状态更新
        self.scan_controller.device_status_changed.connect(self.update_device_status)

        # 扫码状态更新
        self.scan_controller.front_code_received.connect(self._on_front_code_received)
        self.scan_controller.back_code_received.connect(self._on_back_code_received)

        # 验证结果
        self.scan_controller.verification_success.connect(self._on_verification_success)
        self.scan_controller.verification_duplicate.connect(self._on_verification_duplicate)
        self.scan_controller.verification_failed.connect(self._on_verification_failed)
        self.scan_controller.verification_mismatch.connect(self._on_verification_mismatch)

        # 自动定位
        self.scan_controller.auto_locate_barcode.connect(self._on_auto_locate)

        # 扫码状态重置
        self.scan_controller.scan_status_reset.connect(self._on_scan_status_reset)

        # 批次统计更新
        self.scan_controller.batch_stats_updated.connect(self._on_batch_stats_updated)

        # 打印锁定状态更新
        self.scan_controller.print_lock_changed.connect(self._on_print_lock_changed)

    def _on_print_lock_changed(self, is_locked: bool, locked_code: str):
        """打印锁定状态变化"""
        # 检查功能是否启用
        correction_enabled = self.ui_config.is_print_match_correction_enabled()

        if not correction_enabled:
            # 功能未启用，隐藏
            self._lock_title_label.hide()
            self.print_lock_label.hide()
        else:
            # 功能已启用，始终显示
            self._lock_title_label.show()
            self.print_lock_label.show()
            if is_locked and locked_code:
                self.print_lock_label.setText(locked_code)
                self.print_lock_label.setStyleSheet(f"color: {Colors.WARNING};")
            else:
                self.print_lock_label.setText("未锁定")
                self.print_lock_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")

        # 同步更新打印页面的锁定状态
        print_page = self.pages.get("print")
        if print_page and hasattr(print_page, 'on_print_lock_changed'):
            print_page.on_print_lock_changed(is_locked, locked_code)

    def _on_front_code_received(self, code: str):
        """正面扫码数据接收"""
        self.front_scan_status.setText(code)
        self.front_scan_status.setStyleSheet(f"color: {Colors.SUCCESS};")
        # 传递条码到打印页面（用于手动补打）
        print_page = self.pages.get("print")
        if print_page:
            print_page.set_barcode(code)

    def _on_back_code_received(self, code: str):
        """反面扫码数据接收"""
        self.back_scan_status.setText(code)
        self.back_scan_status.setStyleSheet(f"color: {Colors.SUCCESS};")
        # 传递条码到打印页面（用于手动补打）
        print_page = self.pages.get("print")
        if print_page:
            print_page.set_barcode(code)

    def _on_verification_success(self, barcode: str, batch_id: int, batch_name: str):
        """验证成功"""
        self.result_scan_status.setText("验证成功")
        self.result_scan_status.setStyleSheet(f"color: {Colors.SUCCESS};")
        self.set_status(f"验证成功: {barcode}")

        # 显示扫码结果叠加层 + 刷新表格
        scan_page = self.pages.get("scan")
        if scan_page:
            scan_page.show_scan_result("验证成功", "success")
            scan_page.refresh_batch_data(batch_id)  # 刷新对应批次的表格

    def _on_verification_duplicate(self, barcode: str, batch_id: int, batch_name: str):
        """重复扫码"""
        self.result_scan_status.setText("重复扫码")
        self.result_scan_status.setStyleSheet(f"color: {Colors.WARNING};")
        self.set_status(f"重复扫码: {barcode}")

        # 显示扫码结果叠加层 + 刷新表格（扫码次数更新）
        scan_page = self.pages.get("scan")
        if scan_page:
            scan_page.show_scan_result("重复扫码", "warning")
            scan_page.refresh_batch_data(batch_id)  # 刷新对应批次的表格

    def _on_verification_failed(self, barcode: str, error: str):
        """验证失败"""
        self.result_scan_status.setText(error)
        self.result_scan_status.setStyleSheet(f"color: {Colors.ERROR};")
        self.set_status(f"验证失败: {error}")

        # 显示扫码结果叠加层
        scan_page = self.pages.get("scan")
        if scan_page:
            scan_page.show_scan_result(error, "error")

    def _on_verification_mismatch(self, front_code: str, back_code: str):
        """二码不一致"""
        self.result_scan_status.setText("二码不一致")
        self.result_scan_status.setStyleSheet(f"color: {Colors.ERROR};")
        self.set_status(f"二码不一致: 正面={front_code}, 反面={back_code}")

        # 显示扫码结果叠加层
        scan_page = self.pages.get("scan")
        if scan_page:
            scan_page.show_scan_result("二码不一致", "error")

    def _on_auto_locate(self, barcode: str, batch_id: int, batch_name: str):
        """自动定位到条码"""
        scan_page = self.pages.get("scan")
        if scan_page:
            scan_page.locate_barcode(batch_id, barcode)

    def _on_scan_status_reset(self):
        """扫码状态重置"""
        self.front_scan_status.setText("等待扫码")
        self.front_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        self.back_scan_status.setText("等待扫码")
        self.back_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        self.result_scan_status.setText("等待扫码")
        self.result_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")

    def _on_batch_stats_updated(self, batch_id: int, matched_count: int, total_count: int):
        """批次统计更新"""
        scan_page = self.pages.get("scan")
        if scan_page:
            scan_page.update_tab_stats(batch_id, matched_count, total_count)

    def closeEvent(self, event):
        """关闭事件"""
        # 清理扫码控制器资源
        if hasattr(self, 'scan_controller'):
            self.scan_controller.cleanup()
        event.accept()
