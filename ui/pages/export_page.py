"""
数据导出页面
支持扫码日志和生产报告导出，带联动筛选
"""

from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QGridLayout, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os
import subprocess

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


class StatCard(QFrame):
    """统计卡片"""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 80)
        self.label_text = label
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_SM}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setFont(QFont(Fonts.FAMILY, 20))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 数值
        self.value_label = QLabel("0")
        self.value_label.setFont(QFont(Fonts.FAMILY, 18, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {Colors.PRIMARY};")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # 标签
        self.title_label = QLabel(label)
        self.title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        self.title_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

    def set_value(self, value):
        """设置数值"""
        self.value_label.setText(str(value))
        self.value_label.setFont(QFont(Fonts.FAMILY, 18, QFont.Bold))

    def set_text(self, text: str):
        """设置文本"""
        self.value_label.setText(text)
        self.value_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))

    def set_label(self, label: str):
        """设置标签文本"""
        self.title_label.setText(label)


class TypeButton(QPushButton):
    """导出类型按钮"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._is_active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(50)
        self.setMinimumWidth(160)
        self._apply_style()

    def _apply_style(self):
        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Sizes.RADIUS_MD}px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 12px 24px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.SURFACE_LIGHT};
                    color: {Colors.TEXT_PRIMARY_LIGHT};
                    border: 1px solid {Colors.BORDER};
                    border-radius: {Sizes.RADIUS_MD}px;
                    font-size: 16px;
                    padding: 12px 24px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BACKGROUND_LIGHT};
                    border-color: {Colors.PRIMARY};
                }}
            """)

    def set_active(self, active: bool):
        self._is_active = active
        self._apply_style()


class ScanLogFilterPanel(QFrame):
    """扫码日志筛选面板（5级联动）"""

    def __init__(self, query_service, parent=None):
        super().__init__(parent)
        self.query_service = query_service
        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
            }}
        """)

        # 数据缓存
        self.customers = []
        self.containers = []
        self.batches = []

        # 当前选择
        self.selected_customer_ids = []
        self.selected_container_ids = []

        # 时间选择
        self.selected_start_time = None
        self.selected_end_time = None

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 标题
        title = QLabel("扫码日志筛选条件")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        layout.addWidget(title)

        # 筛选条件网格
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        # 第一行：客户 + 货柜
        grid.addWidget(self._create_label("客户:"), 0, 0)
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumHeight(36)
        self.customer_combo.currentTextChanged.connect(self._on_customer_changed)
        grid.addWidget(self.customer_combo, 0, 1)

        grid.addWidget(self._create_label("货柜:"), 0, 2)
        self.container_combo = QComboBox()
        self.container_combo.setMinimumHeight(36)
        self.container_combo.currentTextChanged.connect(self._on_container_changed)
        grid.addWidget(self.container_combo, 0, 3)

        # 第二行：批次 + 结果
        grid.addWidget(self._create_label("批次:"), 1, 0)
        self.batch_combo = QComboBox()
        self.batch_combo.setMinimumHeight(36)
        grid.addWidget(self.batch_combo, 1, 1)

        grid.addWidget(self._create_label("结果:"), 1, 2)
        self.result_combo = QComboBox()
        self.result_combo.setMinimumHeight(36)
        self.result_combo.addItems(["全部", "OK", "NG"])
        grid.addWidget(self.result_combo, 1, 3)

        # 第三行：时间快捷选择
        grid.addWidget(self._create_label("时间:"), 2, 0)
        time_frame = QFrame()
        time_layout = QHBoxLayout(time_frame)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(8)

        time_options = [
            ("今日", self._get_today),
            ("昨日", self._get_yesterday),
            ("三天", self._get_three_days),
            ("本周", self._get_this_week),
            ("本月", self._get_this_month),
        ]

        for label, func in time_options:
            btn = QPushButton(label)
            btn.setMinimumHeight(32)
            btn.setMinimumWidth(60)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.SURFACE_LIGHT};
                    color: {Colors.TEXT_PRIMARY_LIGHT};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 4px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border-color: {Colors.PRIMARY};
                }}
            """)
            # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
            btn.clicked.connect(partial(self._handle_time_click, func, label))
            time_layout.addWidget(btn)

        time_layout.addStretch()
        grid.addWidget(time_frame, 2, 1, 1, 3)

        # 时间显示
        self.time_label = QLabel("未选择时间范围")
        self.time_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        self.time_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        grid.addWidget(self.time_label, 3, 1, 1, 3)

        layout.addLayout(grid)

    def _create_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        label.setMinimumWidth(50)
        return label

    def _load_initial_data(self):
        """加载初始数据"""
        if not self.query_service:
            return

        # 加载客户
        self.customers = self.query_service.get_all_customers()
        self.customer_combo.clear()
        self.customer_combo.addItem("全部", None)
        for c in self.customers:
            self.customer_combo.addItem(c['name'], c['id'])

        # 加载货柜
        self.containers = self.query_service.get_containers_by_customer()
        self.container_combo.clear()
        self.container_combo.addItem("全部", None)
        for c in self.containers:
            self.container_combo.addItem(c, c)

        # 加载批次
        self.batches = self.query_service.get_batches_by_container()
        self.batch_combo.clear()
        self.batch_combo.addItem("全部", None)
        for b in self.batches:
            self.batch_combo.addItem(b['name'], b['id'])

        # 默认选择今日
        start, end = self._get_today()
        self.selected_start_time = start
        self.selected_end_time = end
        self.time_label.setText(f"今日 ({start[:10]} ~ {end[:10]})")

    def _on_customer_changed(self, text: str):
        """客户变更联动"""
        self.container_combo.blockSignals(True)
        self.batch_combo.blockSignals(True)

        # 获取客户ID
        customer_id = self.customer_combo.currentData()
        self.selected_customer_ids = [customer_id] if customer_id else []

        # 更新货柜列表
        self.containers = self.query_service.get_containers_by_customer(customer_id)
        self.container_combo.clear()
        self.container_combo.addItem("全部", None)
        for c in self.containers:
            self.container_combo.addItem(c, c)

        # 更新批次列表
        self._update_batch_list()

        self.container_combo.blockSignals(False)
        self.batch_combo.blockSignals(False)

    def _on_container_changed(self, text: str):
        """货柜变更联动"""
        container_id = self.container_combo.currentData()
        self.selected_container_ids = [container_id] if container_id else []
        self._update_batch_list()

    def _update_batch_list(self):
        """更新批次列表"""
        customer_id = self.selected_customer_ids[0] if self.selected_customer_ids else None
        container_id = self.selected_container_ids[0] if self.selected_container_ids else None

        self.batches = self.query_service.get_batches_by_container(customer_id, container_id)
        self.batch_combo.clear()
        self.batch_combo.addItem("全部", None)
        for b in self.batches:
            self.batch_combo.addItem(b['name'], b['id'])

    def _handle_time_click(self, time_func, label: str, checked: bool = False):
        """时间按钮点击事件处理（兼容 Cython 编译）"""
        self._on_time_clicked(time_func, label)

    def _on_time_clicked(self, time_func, label: str):
        """时间按钮点击"""
        start, end = time_func()
        self.selected_start_time = start
        self.selected_end_time = end
        self.time_label.setText(f"{label} ({start[:10]} ~ {end[:10]})")

    @staticmethod
    def _get_today():
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        end = now.strftime("%Y-%m-%d %H:%M:%S")
        return start, end

    @staticmethod
    def _get_yesterday():
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        end = yesterday.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S")
        return start, end

    @staticmethod
    def _get_three_days():
        now = datetime.now()
        start = (now - timedelta(days=3)).replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        end = now.strftime("%Y-%m-%d %H:%M:%S")
        return start, end

    @staticmethod
    def _get_this_week():
        now = datetime.now()
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        end = now.strftime("%Y-%m-%d %H:%M:%S")
        return start, end

    @staticmethod
    def _get_this_month():
        now = datetime.now()
        start = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        end = now.strftime("%Y-%m-%d %H:%M:%S")
        return start, end

    def get_filter_params(self) -> Dict[str, Any]:
        """获取筛选参数"""
        batch_id = self.batch_combo.currentData()

        result_text = self.result_combo.currentText()
        scan_result = None
        if result_text == "OK":
            scan_result = "pass"
        elif result_text == "NG":
            scan_result = "fail"

        return {
            'customer_ids': self.selected_customer_ids if self.selected_customer_ids else None,
            'container_ids': self.selected_container_ids if self.selected_container_ids else None,
            'batch_ids': [batch_id] if batch_id else None,
            'start_time': self.selected_start_time,
            'end_time': self.selected_end_time,
            'scan_result': scan_result
        }


class ProductionFilterPanel(QFrame):
    """生产报告筛选面板（4级联动）"""

    def __init__(self, query_service, parent=None):
        super().__init__(parent)
        self.query_service = query_service
        self.setStyleSheet("QFrame { background-color: transparent; }")

        # 数据缓存
        self.customers = []
        self.containers = []
        self.batches = []

        # 当前选择
        self.selected_customer_ids = []
        self.selected_container_ids = []

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 标题
        title = QLabel("生产报告筛选条件")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        layout.addWidget(title)

        # 筛选条件网格
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        # 第一行：客户 + 货柜
        grid.addWidget(self._create_label("客户:"), 0, 0)
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumHeight(36)
        self.customer_combo.currentTextChanged.connect(self._on_customer_changed)
        grid.addWidget(self.customer_combo, 0, 1)

        grid.addWidget(self._create_label("货柜:"), 0, 2)
        self.container_combo = QComboBox()
        self.container_combo.setMinimumHeight(36)
        self.container_combo.currentTextChanged.connect(self._on_container_changed)
        grid.addWidget(self.container_combo, 0, 3)

        # 第二行：批次 + 状态
        grid.addWidget(self._create_label("批次:"), 1, 0)
        self.batch_combo = QComboBox()
        self.batch_combo.setMinimumHeight(36)
        grid.addWidget(self.batch_combo, 1, 1)

        grid.addWidget(self._create_label("状态:"), 1, 2)
        self.status_combo = QComboBox()
        self.status_combo.setMinimumHeight(36)
        self.status_combo.addItems(["全部", "已扫", "未扫"])
        grid.addWidget(self.status_combo, 1, 3)

        layout.addLayout(grid)

    def _create_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        label.setMinimumWidth(50)
        return label

    def _load_initial_data(self):
        """加载初始数据"""
        if not self.query_service:
            return

        # 加载客户
        self.customers = self.query_service.get_all_customers()
        self.customer_combo.clear()
        self.customer_combo.addItem("全部", None)
        for c in self.customers:
            self.customer_combo.addItem(c['name'], c['id'])

        # 加载货柜
        self.containers = self.query_service.get_containers_by_customer()
        self.container_combo.clear()
        self.container_combo.addItem("全部", None)
        for c in self.containers:
            self.container_combo.addItem(c, c)

        # 加载批次
        self.batches = self.query_service.get_batches_by_container()
        self.batch_combo.clear()
        self.batch_combo.addItem("全部", None)
        for b in self.batches:
            self.batch_combo.addItem(b['name'], b['id'])

    def _on_customer_changed(self, text: str):
        """客户变更联动"""
        self.container_combo.blockSignals(True)
        self.batch_combo.blockSignals(True)

        customer_id = self.customer_combo.currentData()
        self.selected_customer_ids = [customer_id] if customer_id else []

        self.containers = self.query_service.get_containers_by_customer(customer_id)
        self.container_combo.clear()
        self.container_combo.addItem("全部", None)
        for c in self.containers:
            self.container_combo.addItem(c, c)

        self._update_batch_list()

        self.container_combo.blockSignals(False)
        self.batch_combo.blockSignals(False)

    def _on_container_changed(self, text: str):
        """货柜变更联动"""
        container_id = self.container_combo.currentData()
        self.selected_container_ids = [container_id] if container_id else []
        self._update_batch_list()

    def _update_batch_list(self):
        """更新批次列表"""
        customer_id = self.selected_customer_ids[0] if self.selected_customer_ids else None
        container_id = self.selected_container_ids[0] if self.selected_container_ids else None

        self.batches = self.query_service.get_batches_by_container(customer_id, container_id)
        self.batch_combo.clear()
        self.batch_combo.addItem("全部", None)
        for b in self.batches:
            self.batch_combo.addItem(b['name'], b['id'])

    def get_filter_params(self) -> Dict[str, Any]:
        """获取筛选参数"""
        batch_id = self.batch_combo.currentData()

        status_text = self.status_combo.currentText()
        match_status = None
        if status_text == "已扫":
            match_status = "matched"
        elif status_text == "未扫":
            match_status = "unmatched"

        return {
            'customer_ids': self.selected_customer_ids if self.selected_customer_ids else None,
            'container_ids': self.selected_container_ids if self.selected_container_ids else None,
            'batch_ids': [batch_id] if batch_id else None,
            'match_status': match_status
        }

    def get_selected_names(self) -> Dict[str, List[str]]:
        """获取选中的名称"""
        customer_names = []
        if self.selected_customer_ids:
            for cid in self.selected_customer_ids:
                customer = next((c for c in self.customers if c['id'] == cid), None)
                if customer:
                    customer_names.append(customer['name'])

        return {
            'customer_names': customer_names,
            'container_ids': self.selected_container_ids
        }


class ExportWorker(QThread):
    """导出工作线程"""
    finished = Signal(bool, str)  # 成功/失败, 消息

    def __init__(self, exporter, export_type: str, params: dict, output_path: str):
        super().__init__()
        self.exporter = exporter
        self.export_type = export_type
        self.params = params
        self.output_path = output_path

    def run(self):
        try:
            if self.export_type == "scan_log":
                success = self.exporter.export_scan_logs(self.output_path, **self.params)
            else:
                success = self.exporter.export_production_report(self.output_path, **self.params)

            if success:
                self.finished.emit(True, self.output_path)
            else:
                self.finished.emit(False, "没有符合条件的数据")
        except Exception as e:
            self.finished.emit(False, str(e))


class ExportPage(BasePage):
    """数据导出页面"""

    def __init__(self, db_manager, ui_config, parent=None):
        self.current_export_type = "scan_log"
        self.query_service = None
        self.excel_exporter = None
        self.scan_log_panel = None
        self.production_panel = None
        self.last_export_path = None
        self.export_worker = None
        super().__init__(db_manager, ui_config, parent)

    def _setup_ui(self):
        """设置UI"""
        # 初始化服务
        from core.export_query_service import ExportQueryService
        from core.excel_exporter import ExcelExporter

        if self.db_manager:
            self.query_service = ExportQueryService(self.db_manager)
            self.excel_exporter = ExcelExporter(self.db_manager)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Sizes.SPACING_LG, Sizes.SPACING_LG,
                                  Sizes.SPACING_LG, Sizes.SPACING_LG)
        layout.setSpacing(Sizes.SPACING_MD)

        # 导出类型选择
        self._setup_type_selector(layout)

        # 筛选条件区域
        self._setup_filter_section(layout)

        # 统计和操作区域
        self._setup_action_section(layout)

        # 说明信息
        self._setup_info_section(layout)

        layout.addStretch()

    def _setup_type_selector(self, parent_layout):
        """设置导出类型选择器"""
        type_frame = QFrame()
        type_layout = QHBoxLayout(type_frame)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(16)

        type_layout.addStretch()

        self.scan_log_btn = TypeButton("扫码日志")
        self.scan_log_btn.set_active(True)
        # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
        self.scan_log_btn.clicked.connect(partial(self._handle_type_click, "scan_log"))
        type_layout.addWidget(self.scan_log_btn)

        self.production_btn = TypeButton("生产报告")
        self.production_btn.clicked.connect(partial(self._handle_type_click, "production"))
        type_layout.addWidget(self.production_btn)

        type_layout.addStretch()

        parent_layout.addWidget(type_frame)

    def _setup_filter_section(self, parent_layout):
        """设置筛选条件区域"""
        self.filter_frame = QFrame()
        self.filter_frame.setStyleSheet(f"""
            QFrame#filterFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)
        self.filter_frame.setObjectName("filterFrame")

        self.filter_layout = QVBoxLayout(self.filter_frame)
        self.filter_layout.setContentsMargins(24, 20, 24, 20)
        self.filter_layout.setSpacing(0)

        # 默认显示扫码日志筛选
        self._show_scan_log_filter()

        parent_layout.addWidget(self.filter_frame)

    def _show_scan_log_filter(self):
        """显示扫码日志筛选面板"""
        # 清空
        while self.filter_layout.count():
            item = self.filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.scan_log_panel = ScanLogFilterPanel(self.query_service)
        self.filter_layout.addWidget(self.scan_log_panel)

    def _show_production_filter(self):
        """显示生产报告筛选面板"""
        # 清空
        while self.filter_layout.count():
            item = self.filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.production_panel = ProductionFilterPanel(self.query_service)
        self.filter_layout.addWidget(self.production_panel)

    def _setup_action_section(self, parent_layout):
        """设置统计和操作区域"""
        action_frame = QFrame()
        action_frame.setStyleSheet(f"""
            QFrame#actionFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)
        action_frame.setObjectName("actionFrame")

        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(24, 20, 24, 20)
        action_layout.setSpacing(16)

        # 左侧：统计卡片
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self.total_card = StatCard("", "总计")
        stats_layout.addWidget(self.total_card)

        self.success_card = StatCard("", "成功")
        stats_layout.addWidget(self.success_card)

        self.fail_card = StatCard("", "失败")
        stats_layout.addWidget(self.fail_card)

        self.file_card = StatCard("", "文件")
        self.file_card.set_text("Excel")
        stats_layout.addWidget(self.file_card)

        action_layout.addLayout(stats_layout)
        action_layout.addStretch()

        # 右侧：操作按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        self.export_btn = QPushButton("导出到Excel")
        self.export_btn.setMinimumSize(200, 60)
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.TEXT_MUTED_LIGHT};
            }}
        """)
        self.export_btn.clicked.connect(self._on_export_clicked)
        btn_layout.addWidget(self.export_btn)

        self.open_folder_btn = QPushButton("打开文件夹")
        self.open_folder_btn.setMinimumSize(200, 40)
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE_LIGHT_2};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Sizes.RADIUS_MD}px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BACKGROUND_LIGHT};
            }}
        """)
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        btn_layout.addWidget(self.open_folder_btn)

        action_layout.addLayout(btn_layout)

        parent_layout.addWidget(action_frame)

        # 进度/状态标签
        self.status_label = QLabel("")
        self.status_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        self.status_label.setAlignment(Qt.AlignCenter)
        parent_layout.addWidget(self.status_label)

    def _setup_info_section(self, parent_layout):
        """设置说明信息区域"""
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.INFO}20;
                border: 1px solid {Colors.INFO};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)

        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(8)

        title = QLabel("导出说明")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.INFO}; background: transparent;")
        info_layout.addWidget(title)

        info_text = QLabel(
            "扫码日志：导出所有扫码记录，支持5级联动筛选（客户→货柜→批次→时间→结果）\n"
            "生产报告：显示条码的生产和扫码情况，支持4级联动筛选（客户→货柜→批次→状态）\n"
            "文件格式：Excel (.xlsx)，包含统计汇总和明细数据"
        )
        info_text.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        info_text.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; background: transparent;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)

        parent_layout.addWidget(info_frame)

    def _handle_type_click(self, export_type: str, checked: bool = False):
        """导出类型按钮点击事件处理（兼容 Cython 编译）"""
        self._set_export_type(export_type)

    def _set_export_type(self, export_type: str):
        """设置导出类型"""
        self.current_export_type = export_type

        self.scan_log_btn.set_active(export_type == "scan_log")
        self.production_btn.set_active(export_type == "production")

        if export_type == "scan_log":
            self._show_scan_log_filter()
            self.success_card.set_label("成功")
            self.fail_card.set_label("失败")
        else:
            self._show_production_filter()
            self.success_card.set_label("已扫")
            self.fail_card.set_label("未扫")

    def _on_export_clicked(self):
        """导出按钮点击"""
        if not self.excel_exporter:
            self.status_label.setText("导出器未初始化")
            self.status_label.setStyleSheet(f"color: {Colors.ERROR};")
            return

        # 获取筛选参数
        if self.current_export_type == "scan_log" and self.scan_log_panel:
            params = self.scan_log_panel.get_filter_params()
            from core.excel_exporter import ExcelExporter
            filename = ExcelExporter.generate_scan_log_filename(
                params.get('start_time', ''),
                params.get('end_time', '')
            )
        elif self.current_export_type == "production" and self.production_panel:
            params = self.production_panel.get_filter_params()
            names = self.production_panel.get_selected_names()
            from core.excel_exporter import ExcelExporter
            filename = ExcelExporter.generate_production_report_filename(
                names.get('customer_names', []),
                names.get('container_ids', [])
            )
        else:
            return

        # 选择保存路径
        default_dir = os.path.join(os.path.expanduser("~"), "Desktop", "扫码系统导出")
        if not os.path.exists(default_dir):
            os.makedirs(default_dir, exist_ok=True)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存导出文件",
            os.path.join(default_dir, filename),
            "Excel文件 (*.xlsx)"
        )

        if not file_path:
            return

        # 禁用按钮
        self.export_btn.setEnabled(False)
        self.export_btn.setText("导出中...")
        self.status_label.setText("正在导出数据...")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")

        # 启动导出线程
        self.export_worker = ExportWorker(
            self.excel_exporter,
            self.current_export_type,
            params,
            file_path
        )
        self.export_worker.finished.connect(self._on_export_finished)
        self.export_worker.start()

    def _on_export_finished(self, success: bool, message: str):
        """导出完成回调"""
        self.export_btn.setEnabled(True)
        self.export_btn.setText("导出到Excel")

        if success:
            self.last_export_path = message
            self.status_label.setText("导出成功！")
            self.status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            self.file_card.set_text("已导出")

            # 自动打开文件
            try:
                os.startfile(message)
            except Exception:
                pass
        else:
            self.status_label.setText(f"导出失败: {message}")
            self.status_label.setStyleSheet(f"color: {Colors.ERROR};")

    def _on_open_folder(self):
        """打开文件夹"""
        if self.last_export_path and os.path.exists(self.last_export_path):
            folder = os.path.dirname(self.last_export_path)
            try:
                subprocess.run(['explorer', '/select,', os.path.abspath(self.last_export_path)])
            except Exception:
                subprocess.run(['explorer', folder])
        else:
            default_dir = os.path.join(os.path.expanduser("~"), "Desktop", "扫码系统导出")
            if not os.path.exists(default_dir):
                os.makedirs(default_dir, exist_ok=True)
            subprocess.run(['explorer', default_dir])

    def refresh(self):
        """刷新页面"""
        if self.current_export_type == "scan_log":
            self._show_scan_log_filter()
        else:
            self._show_production_filter()
