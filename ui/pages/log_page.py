"""
日志查看页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QDateEdit, QTabWidget
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


class LogPage(BasePage):
    """日志查看页面"""

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 标签页
        self.tab_widget = QTabWidget()

        # 扫码日志
        self.scan_log_tab = self._create_scan_log_tab()
        self.tab_widget.addTab(self.scan_log_tab, "扫码日志")

        # 系统日志
        self.system_log_tab = self._create_system_log_tab()
        self.tab_widget.addTab(self.system_log_tab, "系统日志")

        # 操作日志
        self.operation_log_tab = self._create_operation_log_tab()
        self.tab_widget.addTab(self.operation_log_tab, "操作日志")

        layout.addWidget(self.tab_widget)

    def _create_scan_log_tab(self):
        """创建扫码日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)

        # 筛选栏
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("扫码枪:"))
        self.scan_port_combo = QComboBox()
        self.scan_port_combo.addItems(["全部", "正面", "反面", "验证"])
        filter_layout.addWidget(self.scan_port_combo)

        filter_layout.addWidget(QLabel("结果:"))
        self.scan_result_combo = QComboBox()
        self.scan_result_combo.addItems(["全部", "等待中", "通过", "重复", "不在批次", "不一致", "失败"])
        filter_layout.addWidget(self.scan_result_combo)

        filter_layout.addWidget(QLabel("日期:"))
        self.scan_start_date = QDateEdit()
        self.scan_start_date.setDate(QDate.currentDate().addDays(-7))
        self.scan_start_date.setCalendarPopup(True)
        filter_layout.addWidget(self.scan_start_date)

        filter_layout.addWidget(QLabel("-"))
        self.scan_end_date = QDateEdit()
        self.scan_end_date.setDate(QDate.currentDate())
        self.scan_end_date.setCalendarPopup(True)
        filter_layout.addWidget(self.scan_end_date)

        filter_layout.addStretch()

        search_btn = QPushButton("查询")
        search_btn.clicked.connect(self._search_scan_logs)
        filter_layout.addWidget(search_btn)

        layout.addLayout(filter_layout)

        # 表格 - 只显示核心字段：时间、扫码枪、扫码数据、结果
        self.scan_log_table = QTableWidget()
        self.scan_log_table.setColumnCount(4)
        self.scan_log_table.setHorizontalHeaderLabels([
            "时间", "扫码枪", "扫码数据", "结果"
        ])
        header = self.scan_log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.scan_log_table.setColumnWidth(0, 180)
        self.scan_log_table.setColumnWidth(1, 80)
        self.scan_log_table.setColumnWidth(2, 200)
        self.scan_log_table.setAlternatingRowColors(True)
        layout.addWidget(self.scan_log_table)

        return tab

    def _create_system_log_tab(self):
        """创建系统日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)

        # 筛选栏
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("级别:"))
        self.system_level_combo = QComboBox()
        self.system_level_combo.addItems(["全部", "INFO", "WARNING", "ERROR", "DEBUG"])
        filter_layout.addWidget(self.system_level_combo)

        filter_layout.addWidget(QLabel("关键词:"))
        self.system_keyword_input = QLineEdit()
        self.system_keyword_input.setPlaceholderText("搜索...")
        filter_layout.addWidget(self.system_keyword_input)

        filter_layout.addStretch()

        search_btn = QPushButton("查询")
        search_btn.clicked.connect(self._search_system_logs)
        filter_layout.addWidget(search_btn)

        clear_btn = QPushButton("清除日志")
        clear_btn.setProperty("danger", True)
        clear_btn.clicked.connect(self._clear_system_logs)
        filter_layout.addWidget(clear_btn)

        layout.addLayout(filter_layout)

        # 表格
        self.system_log_table = QTableWidget()
        self.system_log_table.setColumnCount(4)
        self.system_log_table.setHorizontalHeaderLabels(["时间", "级别", "来源", "消息"])
        self.system_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.system_log_table.setAlternatingRowColors(True)
        layout.addWidget(self.system_log_table)

        return tab

    def _create_operation_log_tab(self):
        """创建操作日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)

        # 筛选栏
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("操作:"))
        self.operation_action_combo = QComboBox()
        self.operation_action_combo.addItems(["全部", "用户登录", "创建批次", "修改用户", "其他"])
        filter_layout.addWidget(self.operation_action_combo)

        filter_layout.addWidget(QLabel("关键词:"))
        self.operation_keyword_input = QLineEdit()
        self.operation_keyword_input.setPlaceholderText("搜索...")
        filter_layout.addWidget(self.operation_keyword_input)

        filter_layout.addStretch()

        search_btn = QPushButton("查询")
        search_btn.clicked.connect(self._search_operation_logs)
        filter_layout.addWidget(search_btn)

        layout.addLayout(filter_layout)

        # 表格
        self.operation_log_table = QTableWidget()
        self.operation_log_table.setColumnCount(5)
        self.operation_log_table.setHorizontalHeaderLabels(["时间", "用户", "操作", "目标", "详情"])
        self.operation_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.operation_log_table.setAlternatingRowColors(True)
        layout.addWidget(self.operation_log_table)

        return tab

    def _search_scan_logs(self):
        """搜索扫码日志"""
        port_filter = self.scan_port_combo.currentText()
        result_filter = self.scan_result_combo.currentText()
        start_date = self.scan_start_date.date().toString("yyyy-MM-dd")
        end_date = self.scan_end_date.date().toString("yyyy-MM-dd")

        # 端口映射
        port_map = {"全部": None, "正面": "front", "反面": "back", "验证": "verify"}
        scanner_port = port_map.get(port_filter)

        # 结果映射
        result_map = {
            "全部": None, "等待中": "waiting", "通过": "pass",
            "重复": "duplicate", "不在批次": "not_found", "不一致": "mismatch", "失败": "fail"
        }
        scan_result = result_map.get(result_filter)

        logs = self.db_manager.get_scan_logs(
            start_time=f"{start_date} 00:00:00",
            end_time=f"{end_date} 23:59:59",
            scan_result=scan_result,
            scanner_port=scanner_port
        )

        # 扫码枪显示名称
        port_names = {"front": "正面", "back": "反面", "verify": "验证"}

        self.scan_log_table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            # 时间
            self.scan_log_table.setItem(row, 0, QTableWidgetItem(str(log.get('scan_time', '-'))))
            # 扫码枪
            port = log.get('scanner_port', '')
            port_name = port_names.get(port, port or '-')
            self.scan_log_table.setItem(row, 1, QTableWidgetItem(port_name))
            # 扫码数据
            scan_data = log.get('scan_data') or log.get('barcode', '-')
            self.scan_log_table.setItem(row, 2, QTableWidgetItem(scan_data))
            # 结果
            result_msg = log.get('result_message') or log.get('scan_result', '-')
            self.scan_log_table.setItem(row, 3, QTableWidgetItem(result_msg))

    def _search_system_logs(self):
        """搜索系统日志"""
        level = self.system_level_combo.currentText()
        keyword = self.system_keyword_input.text().strip()

        logs = self.db_manager.get_system_logs(
            level=level if level != "全部" else None,
            keyword=keyword if keyword else None
        )

        self.system_log_table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            self.system_log_table.setItem(row, 0, QTableWidgetItem(str(log.get('created_at', '-'))))
            self.system_log_table.setItem(row, 1, QTableWidgetItem(log.get('level', '-')))
            self.system_log_table.setItem(row, 2, QTableWidgetItem(log.get('source', '-')))
            self.system_log_table.setItem(row, 3, QTableWidgetItem(log.get('message', '-')))

    def _search_operation_logs(self):
        """搜索操作日志"""
        action = self.operation_action_combo.currentText()
        keyword = self.operation_keyword_input.text().strip()

        logs = self.db_manager.get_operation_logs(
            action=action if action != "全部" else None,
            keyword=keyword if keyword else None
        )

        self.operation_log_table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            self.operation_log_table.setItem(row, 0, QTableWidgetItem(str(log.get('created_at', '-'))))
            self.operation_log_table.setItem(row, 1, QTableWidgetItem(log.get('username', '-')))
            self.operation_log_table.setItem(row, 2, QTableWidgetItem(log.get('action', '-')))
            self.operation_log_table.setItem(row, 3, QTableWidgetItem(log.get('target_type', '-')))
            self.operation_log_table.setItem(row, 4, QTableWidgetItem(log.get('details', '-')))

    def _clear_system_logs(self):
        """清除系统日志"""
        if self.show_message("确认", "确定要清除所有系统日志吗？", "question"):
            if self.db_manager.clear_old_logs("system", 0):
                self._search_system_logs()
                self.show_message("成功", "日志已清除", "info")
            else:
                self.show_message("错误", "清除失败", "error")

    def refresh(self):
        """刷新页面"""
        self._search_scan_logs()
