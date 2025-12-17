"""
客户管理页面
"""

from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QDialog, QFormLayout, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


class CustomerPage(BasePage):
    """客户管理页面"""

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 工具栏
        self._setup_toolbar(layout)

        # 客户列表
        self._setup_customer_table(layout)

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

        # 新建客户按钮
        create_btn = QPushButton("+ 新建客户")
        create_btn.clicked.connect(self._show_create_dialog)
        toolbar_layout.addWidget(create_btn)

        toolbar_layout.addStretch()

        # 搜索
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索客户名称...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self._apply_filter)
        toolbar_layout.addWidget(self.search_input)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.clicked.connect(self.refresh)
        toolbar_layout.addWidget(refresh_btn)

        parent_layout.addWidget(toolbar)

    def _setup_customer_table(self, parent_layout):
        """设置客户表格"""
        table_frame = QFrame()
        table_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)

        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(16, 16, 16, 16)

        self.customer_table = QTableWidget()
        self.customer_table.setColumnCount(5)
        self.customer_table.setHorizontalHeaderLabels([
            "客户名称", "备注", "创建时间", "状态", "操作"
        ])
        self.customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.customer_table.verticalHeader().setDefaultSectionSize(44)  # 设置行高
        self.customer_table.setAlternatingRowColors(True)
        self.customer_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.customer_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 只读模式

        table_layout.addWidget(self.customer_table)
        parent_layout.addWidget(table_frame)

    def _show_create_dialog(self):
        """显示创建客户对话框"""
        dialog = CustomerDialog(self.db_manager, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()
            self.show_message("成功", "客户创建成功", "info")

    def _apply_filter(self):
        """应用筛选"""
        self._load_customers()

    def _load_customers(self):
        """加载客户数据"""
        keyword = self.search_input.text().strip().lower()
        customers = self.db_manager.get_all_customers(active_only=False)

        # 关键词过滤
        if keyword:
            customers = [c for c in customers if keyword in c['customer_name'].lower()]

        self.customer_table.setRowCount(len(customers))

        for row, customer in enumerate(customers):
            self.customer_table.setItem(row, 0, QTableWidgetItem(customer['customer_name']))
            self.customer_table.setItem(row, 1, QTableWidgetItem(customer.get('notes', '-')))
            self.customer_table.setItem(row, 2, QTableWidgetItem(str(customer.get('created_at', '-'))))

            status_text = "启用" if customer['is_active'] else "禁用"
            status_item = QTableWidgetItem(status_text)
            if not customer['is_active']:
                status_item.setForeground(Qt.red)
            self.customer_table.setItem(row, 3, status_item)

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)

            # 表格内按钮样式（覆盖全局样式的padding和min-height）
            table_btn_style = "padding: 4px 8px; min-height: 0px;"

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(50, 40)
            edit_btn.setStyleSheet(table_btn_style)
            # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
            edit_btn.clicked.connect(partial(self._on_edit_clicked, customer['id']))
            btn_layout.addWidget(edit_btn)

            if customer['is_active']:
                disable_btn = QPushButton("禁用")
                disable_btn.setFixedSize(50, 40)
                disable_btn.setStyleSheet(table_btn_style)
                disable_btn.clicked.connect(partial(self._on_disable_clicked, customer['id']))
                btn_layout.addWidget(disable_btn)
            else:
                enable_btn = QPushButton("启用")
                enable_btn.setFixedSize(50, 40)
                enable_btn.setStyleSheet(table_btn_style)
                enable_btn.clicked.connect(partial(self._on_enable_clicked, customer['id']))
                btn_layout.addWidget(enable_btn)

            self.customer_table.setCellWidget(row, 4, btn_widget)

    def _on_edit_clicked(self, customer_id: int, checked: bool = False):
        """编辑按钮点击事件处理（兼容 Cython 编译）"""
        self._edit_customer(customer_id)

    def _on_disable_clicked(self, customer_id: int, checked: bool = False):
        """禁用按钮点击事件处理（兼容 Cython 编译）"""
        self._disable_customer(customer_id)

    def _on_enable_clicked(self, customer_id: int, checked: bool = False):
        """启用按钮点击事件处理（兼容 Cython 编译）"""
        self._enable_customer(customer_id)

    def _edit_customer(self, customer_id: int):
        """编辑客户"""
        customer = self.db_manager.get_customer_by_id(customer_id)
        if customer:
            dialog = CustomerDialog(self.db_manager, self, customer)
            if dialog.exec() == QDialog.Accepted:
                self.refresh()
                self.show_message("成功", "客户信息已更新", "info")

    def _disable_customer(self, customer_id: int):
        """禁用客户"""
        if self.show_message("确认", "确定要禁用此客户吗？", "question"):
            if self.db_manager.delete_customer(customer_id):
                self.refresh()
                self.show_message("成功", "客户已禁用", "info")
            else:
                self.show_message("错误", "操作失败", "error")

    def _enable_customer(self, customer_id: int):
        """启用客户"""
        if self.db_manager.activate_customer(customer_id):
            self.refresh()
            self.show_message("成功", "客户已启用", "info")
        else:
            self.show_message("错误", "操作失败", "error")

    def refresh(self):
        """刷新页面"""
        self._load_customers()


class CustomerDialog(QDialog):
    """客户对话框（新建/编辑）"""

    def __init__(self, db_manager, parent=None, customer=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.customer = customer
        self.setWindowTitle("编辑客户" if customer else "新建客户")
        self.setFixedSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        # 客户名称
        self.name_input = QLineEdit()
        if self.customer:
            self.name_input.setText(self.customer['customer_name'])
        form_layout.addRow("客户名称:", self.name_input)

        # 备注
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        if self.customer:
            self.notes_input.setText(self.customer.get('notes', ''))
        form_layout.addRow("备注:", self.notes_input)

        layout.addLayout(form_layout)
        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save(self):
        """保存"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入客户名称")
            return

        notes = self.notes_input.toPlainText().strip()

        if self.customer:
            # 更新
            success = self.db_manager.update_customer(
                self.customer['id'],
                customer_name=name,
                notes=notes
            )
        else:
            # 新建
            success = self.db_manager.add_customer(
                customer_name=name,
                notes=notes
            )

        if success:
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "保存失败")
