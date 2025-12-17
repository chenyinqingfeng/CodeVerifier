"""
批次管理页面 - 数据库版本
完全基于数据库管理批次，支持树形结构显示
"""

from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QGroupBox, QFormLayout, QSpinBox,
    QDialog, QMessageBox, QFileDialog, QAbstractItemView,
    QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QIcon

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


# 批次状态常量
STATUS_PENDING = 0   # 待激活
STATUS_ACTIVE = 1    # 活动中
STATUS_ARCHIVED = 2  # 已归档

STATUS_NAMES = {
    STATUS_PENDING: "待激活",
    STATUS_ACTIVE: "活动中",
    STATUS_ARCHIVED: "已归档"
}

STATUS_COLORS = {
    STATUS_PENDING: Colors.TEXT_MUTED_LIGHT,
    STATUS_ACTIVE: Colors.SUCCESS,
    STATUS_ARCHIVED: Colors.WARNING
}


class FilterButton(QPushButton):
    """筛选按钮"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._is_active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(36)
        self._apply_style()

    def _apply_style(self):
        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Sizes.RADIUS_SM}px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.TEXT_PRIMARY_LIGHT};
                    border: 1px solid {Colors.BORDER};
                    border-radius: {Sizes.RADIUS_SM}px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BACKGROUND_LIGHT};
                    border-color: {Colors.PRIMARY};
                }}
            """)

    def set_active(self, active: bool):
        self._is_active = active
        self._apply_style()


class BatchPage(BasePage):
    """批次管理页面"""

    def __init__(self, db_manager, ui_config, parent=None):
        self._loading = True  # 防止初始化时触发保存
        self.current_filter = STATUS_ACTIVE  # 默认显示活动中
        self.selected_batch_ids = set()
        self.selected_container_key = None  # 选中的货柜 (customer_name, container_id)
        self.selection_type = None  # 'batch', 'container', 或 None
        self.tree_node_to_batch = {}  # tree_item -> batch_id
        self.tree_node_to_container = {}  # tree_item -> (customer_name, container_id)
        self.container_batches = {}  # (customer_name, container_id) -> [batch_ids]
        super().__init__(db_manager, ui_config, parent)
        self._loading = False

    def _invalidate_scan_cache(self):
        """使扫码验证页面缓存失效"""
        if self.main_window and hasattr(self.main_window, 'pages'):
            scan_page = self.main_window.pages.get('scan')
            if scan_page and hasattr(scan_page, 'invalidate_cache'):
                scan_page.invalidate_cache()

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Sizes.SPACING_LG, Sizes.SPACING_LG,
                                  Sizes.SPACING_LG, Sizes.SPACING_LG)
        layout.setSpacing(Sizes.SPACING_MD)

        # 左侧：创建批次表单
        self._setup_create_panel(layout)

        # 右侧：批次列表
        self._setup_list_panel(layout)

    def _setup_create_panel(self, parent_layout):
        """设置创建批次面板"""
        create_frame = QFrame()
        create_frame.setFixedWidth(380)
        create_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)

        create_layout = QVBoxLayout(create_frame)
        create_layout.setContentsMargins(20, 20, 20, 20)
        create_layout.setSpacing(16)

        # 标题
        title = QLabel("创建新批次")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        create_layout.addWidget(title)

        # 表单
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # 客户选择
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumHeight(36)
        form_layout.addRow("客户:", self.customer_combo)

        # 货柜号
        self.container_input = QLineEdit()
        self.container_input.setPlaceholderText("输入货柜号")
        self.container_input.setMinimumHeight(36)
        form_layout.addRow("货柜号:", self.container_input)

        # 条码前缀
        self.prefix_input = QLineEdit()
        self.prefix_input.setText("K00J")
        self.prefix_input.setMinimumHeight(36)
        form_layout.addRow("前缀:", self.prefix_input)

        # 起始编号
        self.start_input = QLineEdit()
        self.start_input.setText("00001")
        self.start_input.setMinimumHeight(36)
        form_layout.addRow("起始编号:", self.start_input)

        # 结束编号
        self.end_input = QLineEdit()
        self.end_input.setText("00100")
        self.end_input.setMinimumHeight(36)
        form_layout.addRow("结束编号:", self.end_input)

        # 后缀
        self.suffix_input = QLineEdit()
        self.suffix_input.setText("ADBC")
        self.suffix_input.setMinimumHeight(36)
        form_layout.addRow("后缀:", self.suffix_input)

        create_layout.addLayout(form_layout)

        # 预览
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: {Sizes.RADIUS_SM}px;
                padding: 12px;
            }}
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 12, 12, 12)

        preview_title = QLabel("条码预览")
        preview_title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        preview_layout.addWidget(preview_title)

        self.preview_label = QLabel("-")
        self.preview_label.setFont(QFont(Fonts.FAMILY_MONO, Fonts.SIZE_SM))
        self.preview_label.setStyleSheet(f"color: {Colors.PRIMARY};")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)

        create_layout.addWidget(preview_frame)

        # 连接信号更新预览和自动保存
        self.prefix_input.textChanged.connect(self._update_preview)
        self.prefix_input.textChanged.connect(self._save_batch_params)
        self.start_input.textChanged.connect(self._update_preview)
        self.start_input.textChanged.connect(self._save_batch_params)
        self.end_input.textChanged.connect(self._update_preview)
        self.end_input.textChanged.connect(self._save_batch_params)
        self.suffix_input.textChanged.connect(self._update_preview)
        self.suffix_input.textChanged.connect(self._save_batch_params)
        self.container_input.textChanged.connect(self._save_batch_params)
        self.customer_combo.currentIndexChanged.connect(self._save_batch_params)
        self._update_preview()

        create_layout.addStretch()

        # 创建按钮
        create_btn = QPushButton("创建批次")
        create_btn.setMinimumHeight(44)
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                font-size: {Fonts.SIZE_BASE}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        create_btn.clicked.connect(self._create_batch)
        create_layout.addWidget(create_btn)

        parent_layout.addWidget(create_frame)

    def _setup_list_panel(self, parent_layout):
        """设置批次列表面板"""
        list_frame = QFrame()
        list_frame.setStyleSheet(f"""
            QFrame#listFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)
        list_frame.setObjectName("listFrame")

        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(20, 20, 20, 20)
        list_layout.setSpacing(16)

        # 标题行
        header_layout = QHBoxLayout()

        title = QLabel("批次列表")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        list_layout.addLayout(header_layout)

        # 工具栏
        self._setup_toolbar(list_layout)

        # 批次树形列表
        self._setup_batch_tree(list_layout)

        parent_layout.addWidget(list_frame)

    def _setup_toolbar(self, parent_layout):
        """设置工具栏"""
        toolbar = QFrame()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)

        # 筛选按钮组
        self.filter_pending_btn = FilterButton("⏸ 待激活")
        # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
        self.filter_pending_btn.clicked.connect(partial(self._on_filter_clicked, STATUS_PENDING))
        toolbar_layout.addWidget(self.filter_pending_btn)

        self.filter_active_btn = FilterButton("▶ 活动中")
        self.filter_active_btn.set_active(True)
        self.filter_active_btn.clicked.connect(partial(self._on_filter_clicked, STATUS_ACTIVE))
        toolbar_layout.addWidget(self.filter_active_btn)

        self.filter_archived_btn = FilterButton("📦 已归档")
        self.filter_archived_btn.clicked.connect(partial(self._on_filter_clicked, STATUS_ARCHIVED))
        toolbar_layout.addWidget(self.filter_archived_btn)

        toolbar_layout.addStretch()

        # 操作按钮
        # 编辑按钮
        self.edit_btn = QPushButton("✏ 编辑")
        self.edit_btn.setMinimumHeight(36)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._edit_selected)
        toolbar_layout.addWidget(self.edit_btn)

        # 详情按钮
        self.detail_btn = QPushButton("📋 详情")
        self.detail_btn.setMinimumHeight(36)
        self.detail_btn.setEnabled(False)
        self.detail_btn.clicked.connect(self._show_detail)
        toolbar_layout.addWidget(self.detail_btn)

        # 归档按钮
        self.archive_btn = QPushButton("📦 归档")
        self.archive_btn.setMinimumHeight(36)
        self.archive_btn.setEnabled(False)
        self.archive_btn.clicked.connect(self._archive_selected)
        toolbar_layout.addWidget(self.archive_btn)

        # 激活按钮（待激活页面显示）
        self.activate_btn = QPushButton("▶ 激活")
        self.activate_btn.setMinimumHeight(36)
        self.activate_btn.setEnabled(False)
        self.activate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {Colors.SUCCESS_DARK};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
            }}
        """)
        self.activate_btn.clicked.connect(self._activate_selected)
        self.activate_btn.hide()
        toolbar_layout.addWidget(self.activate_btn)

        # 回档按钮（已归档页面显示）
        self.unarchive_btn = QPushButton("↩ 回档")
        self.unarchive_btn.setMinimumHeight(36)
        self.unarchive_btn.setEnabled(False)
        self.unarchive_btn.clicked.connect(self._unarchive_selected)
        self.unarchive_btn.hide()
        toolbar_layout.addWidget(self.unarchive_btn)

        # 取消激活按钮（活动中页面显示）
        self.cancel_btn = QPushButton("⏸ 取消")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_selected)
        toolbar_layout.addWidget(self.cancel_btn)

        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setMinimumHeight(36)
        refresh_btn.clicked.connect(self.refresh)
        toolbar_layout.addWidget(refresh_btn)

        parent_layout.addWidget(toolbar)

    def _setup_batch_tree(self, parent_layout):
        """设置批次树形列表"""
        self.batch_tree = QTreeWidget()
        self.batch_tree.setHeaderLabels(["客户 / 货柜 / 批次", "状态", "总数", "已扫", "未扫", "进度"])
        self.batch_tree.setAlternatingRowColors(True)
        self.batch_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.batch_tree.setRootIsDecorated(True)
        self.batch_tree.setIndentation(20)

        # 设置列宽（减小固定列宽度，让批次名称列有更多空间）
        header = self.batch_tree.header()
        header.setStretchLastSection(False)  # 禁用最后一列自动拉伸！
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 只有批次名称列自动拉伸
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.batch_tree.setColumnWidth(1, 50)   # 状态
        self.batch_tree.setColumnWidth(2, 45)   # 总数
        self.batch_tree.setColumnWidth(3, 45)   # 已扫
        self.batch_tree.setColumnWidth(4, 45)   # 未扫
        self.batch_tree.setColumnWidth(5, 55)   # 进度

        # 设置表头对齐方式
        header_item = self.batch_tree.headerItem()
        header_item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        for col in range(1, 6):
            header_item.setTextAlignment(col, Qt.AlignCenter)

        # 样式
        self.batch_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colors.SURFACE_LIGHT};
                border: none;
                font-size: {Fonts.SIZE_SM}px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 6px 2px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTreeWidget::item:hover {{
                background-color: {Colors.BACKGROUND_LIGHT};
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
            QTreeWidget::item:selected:hover {{
                background-color: {Colors.PRIMARY_HOVER};
                color: white;
            }}
            QTreeWidget::item:selected:active {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
            QTreeWidget::branch:selected {{
                background-color: {Colors.PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                font-weight: bold;
                padding: 6px 4px;
                border: none;
                border-bottom: 2px solid {Colors.BORDER};
            }}
        """)

        # 连接选择信号
        self.batch_tree.itemSelectionChanged.connect(self._on_selection_changed)

        parent_layout.addWidget(self.batch_tree)

    def _load_customers(self):
        """加载客户列表"""
        self.customer_combo.clear()
        self.customer_combo.addItem("未指定", None)

        try:
            customers = self.db_manager.get_all_customers()
            for customer in customers:
                self.customer_combo.addItem(customer['customer_name'], customer['id'])
        except Exception as e:
            self.set_status(f"加载客户失败: {e}")

    def _update_preview(self):
        """更新条码预览"""
        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()
        start_str = self.start_input.text().strip()
        end_str = self.end_input.text().strip()

        if not start_str or not end_str:
            self.preview_label.setStyleSheet(f"color: {Colors.PRIMARY};")
            self.preview_label.setText("-")
            return

        try:
            start = int(start_str)
            end = int(end_str)
        except ValueError:
            self.preview_label.setStyleSheet(f"color: {Colors.ERROR};")
            self.preview_label.setText("请输入有效的编号\n条码无法生成")
            return

        # 检查格式一致性：只要起始有前导零，就检查位数是否一致
        start_has_zero = start_str.startswith('0') and len(start_str) > 1

        if start_has_zero and len(start_str) != len(end_str):
            self.preview_label.setStyleSheet(f"color: {Colors.ERROR};")
            self.preview_label.setText("位数不一致！\n条码无法生成")
            return

        if end < start:
            self.preview_label.setStyleSheet(f"color: {Colors.ERROR};")
            self.preview_label.setText("结束不能小于起始\n条码无法生成")
            return

        count = end - start + 1

        # 恢复正常颜色
        self.preview_label.setStyleSheet(f"color: {Colors.PRIMARY};")

        # 生成预览
        if start_has_zero:
            num_digits = len(start_str)
            first_code = f"{prefix}{str(start).zfill(num_digits)}{suffix}"
            last_code = f"{prefix}{str(end).zfill(num_digits)}{suffix}"
        else:
            first_code = f"{prefix}{start}{suffix}"
            last_code = f"{prefix}{end}{suffix}"

        self.preview_label.setText(f"{first_code} ~ {last_code}\n共 {count} 条")

    def _on_filter_clicked(self, filter_type: int, checked: bool = False):
        """筛选按钮点击事件处理（兼容 Cython 编译）"""
        self._set_filter(filter_type)

    def _set_filter(self, filter_type: int):
        """设置筛选器"""
        self.current_filter = filter_type

        # 更新按钮状态
        self.filter_pending_btn.set_active(filter_type == STATUS_PENDING)
        self.filter_active_btn.set_active(filter_type == STATUS_ACTIVE)
        self.filter_archived_btn.set_active(filter_type == STATUS_ARCHIVED)

        # 清空选择
        self.selected_batch_ids.clear()
        self._update_action_buttons()

        # 显示/隐藏状态操作按钮
        self.activate_btn.hide()
        self.cancel_btn.hide()
        self.unarchive_btn.hide()
        self.archive_btn.show()

        if filter_type == STATUS_PENDING:
            self.activate_btn.show()
        elif filter_type == STATUS_ACTIVE:
            self.cancel_btn.show()
        elif filter_type == STATUS_ARCHIVED:
            self.unarchive_btn.show()
            self.archive_btn.hide()

        # 刷新列表
        self._load_batch_list()

    def _load_batch_list(self):
        """加载批次列表（树形结构）"""
        self.batch_tree.clear()
        self.tree_node_to_batch.clear()
        self.tree_node_to_container.clear()
        self.container_batches.clear()

        try:
            # 查询批次数据 - 直接使用整数状态值（数据库存储的是整数：0=待激活, 1=活动中, 2=已归档）
            batches = self.db_manager.execute_query("""
                SELECT
                    b.id,
                    b.batch_name,
                    b.container_id,
                    c.customer_name,
                    b.total_count,
                    b.matched_count,
                    b.status
                FROM batches b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.status = ?
                ORDER BY c.customer_name, b.container_id, b.batch_name
            """, (self.current_filter,))

            # 按客户和货柜分组
            customer_items = {}  # customer_name -> QTreeWidgetItem
            container_items = {}  # (customer_name, container_id) -> QTreeWidgetItem

            for row in batches:
                batch_id, batch_name, container_id, customer_name, total_count, matched_count, status = row
                customer_name = customer_name or '未指定'
                container_id = container_id or '无货柜'
                total_count = total_count or 0
                matched_count = matched_count or 0
                unmatched = total_count - matched_count
                # 计算进度百分比
                if total_count > 0:
                    percent = matched_count * 100 // total_count
                    progress = f"{percent}%"
                else:
                    progress = "-"

                # 创建或获取客户节点
                if customer_name not in customer_items:
                    customer_item = QTreeWidgetItem(self.batch_tree, [f"👤 {customer_name}", "", "", "", "", ""])
                    customer_item.setFont(0, QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
                    customer_item.setExpanded(True)
                    customer_items[customer_name] = customer_item

                # 创建或获取货柜节点
                container_key = (customer_name, container_id)
                if container_key not in container_items:
                    container_item = QTreeWidgetItem(customer_items[customer_name], [f"📦 {container_id}", "", "", "", "", ""])
                    container_item.setExpanded(True)
                    container_items[container_key] = container_item
                    self.tree_node_to_container[id(container_item)] = container_key
                    self.container_batches[container_key] = []

                # 创建批次节点
                status_text = STATUS_NAMES.get(self.current_filter, "-")
                batch_item = QTreeWidgetItem(container_items[container_key], [
                    f"📄 {batch_name}",
                    status_text,
                    str(total_count),
                    str(matched_count),
                    str(unmatched),
                    progress
                ])

                # 设置对齐
                for col in range(1, 6):
                    batch_item.setTextAlignment(col, Qt.AlignCenter)

                # 设置颜色
                status_color = STATUS_COLORS.get(self.current_filter, Colors.TEXT_MUTED_LIGHT)
                batch_item.setForeground(1, QColor(status_color))

                # 进度列：加粗，100%显示绿色
                progress_font = QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold)
                batch_item.setFont(5, progress_font)
                if total_count > 0 and matched_count >= total_count:
                    batch_item.setForeground(5, QColor("#10b981"))  # 绿色
                else:
                    batch_item.setForeground(5, QColor("#1f2937"))  # 深灰色

                self.tree_node_to_batch[id(batch_item)] = batch_id
                self.container_batches[container_key].append(batch_id)

        except Exception as e:
            self.set_status(f"加载批次失败: {e}")

    def _on_selection_changed(self):
        """选择变化事件"""
        self.selected_batch_ids.clear()
        self.selected_container_key = None  # 记录选中的货柜
        self.selection_type = None  # 'batch', 'container', 或 None

        selected_items = self.batch_tree.selectedItems()

        # 只有单选才处理编辑
        if len(selected_items) == 1:
            item = selected_items[0]
            item_id = id(item)

            if item_id in self.tree_node_to_batch:
                # 单选批次节点
                self.selected_batch_ids.add(self.tree_node_to_batch[item_id])
                self.selection_type = 'batch'
            elif item_id in self.tree_node_to_container:
                # 单选货柜节点
                container_key = self.tree_node_to_container[item_id]
                self.selected_container_key = container_key
                if container_key in self.container_batches:
                    self.selected_batch_ids.update(self.container_batches[container_key])
                self.selection_type = 'container'
        else:
            # 多选情况，收集所有批次ID（用于其他操作如归档）
            for item in selected_items:
                item_id = id(item)
                if item_id in self.tree_node_to_batch:
                    self.selected_batch_ids.add(self.tree_node_to_batch[item_id])
                elif item_id in self.tree_node_to_container:
                    container_key = self.tree_node_to_container[item_id]
                    if container_key in self.container_batches:
                        self.selected_batch_ids.update(self.container_batches[container_key])

        self._update_action_buttons()

    def _update_action_buttons(self):
        """更新操作按钮状态"""
        has_selection = len(self.selected_batch_ids) > 0

        # 编辑按钮：只有单选批次或单选货柜时才启用
        can_edit = self.selection_type in ('batch', 'container')
        self.edit_btn.setEnabled(can_edit)

        self.detail_btn.setEnabled(has_selection)
        self.archive_btn.setEnabled(has_selection)
        self.activate_btn.setEnabled(has_selection)
        self.cancel_btn.setEnabled(has_selection)
        self.unarchive_btn.setEnabled(has_selection)

    def _create_batch(self):
        """创建批次"""
        container_id = self.container_input.text().strip() or None  # 允许为空
        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()
        start_str = self.start_input.text().strip()
        end_str = self.end_input.text().strip()

        # 只有起始编号和结束编号是必填的
        if not start_str or not end_str:
            self.show_message("提示", "请输入起始编号和结束编号", "warning")
            return

        try:
            start = int(start_str)
            end = int(end_str)
        except ValueError:
            self.show_message("提示", "请输入有效的编号", "warning")
            return

        if end < start:
            self.show_message("提示", "结束编号不能小于起始编号", "warning")
            return

        customer_id = self.customer_combo.currentData()

        # 检查格式一致性：只要起始有前导零，就检查位数是否一致
        start_has_zero = start_str.startswith('0') and len(start_str) > 1

        if start_has_zero and len(start_str) != len(end_str):
            self.show_message("格式错误", f"起始编号与结束编号位数不一致！\n起始: {len(start_str)}位，结束: {len(end_str)}位", "warning")
            return

        # 确定编号位数
        if start_has_zero:
            num_digits = len(start_str)
        else:
            num_digits = 0  # 不补零

        # 生成批次名称（显示完整的第一个和最后一个条码）
        first_barcode = f"{prefix}{start_str}{suffix}"
        last_barcode = f"{prefix}{end_str}{suffix}"
        batch_name = f"{first_barcode}-{last_barcode}"

        try:
            batch_id = self.db_manager.create_batch(
                batch_name=batch_name,
                customer_id=customer_id,
                container_id=container_id,
                prefix=prefix,
                suffix=suffix,
                start_number=start,
                end_number=end,
                num_digits=num_digits
            )

            if batch_id:
                self.refresh()
                self.show_message("成功", f"批次 {batch_name} 创建成功", "info")
                # 清空表单
                self.container_input.clear()
            else:
                self.show_message("错误", "创建失败，批次名称可能已存在", "error")
        except Exception as e:
            self.show_message("错误", f"创建失败: {e}", "error")

    def _activate_selected(self):
        """激活选中的批次"""
        if not self.selected_batch_ids:
            return

        count = len(self.selected_batch_ids)
        if not self.show_message("确认", f"确定要激活选中的 {count} 个批次吗？", "question"):
            return

        try:
            for batch_id in self.selected_batch_ids:
                self.db_manager.execute_update(
                    "UPDATE batches SET status = ? WHERE id = ?",
                    (STATUS_ACTIVE, batch_id)
                )
            self._invalidate_scan_cache()  # 使扫码页面缓存失效
            self.refresh()
            self.show_message("成功", f"已激活 {count} 个批次", "info")
        except Exception as e:
            self.show_message("错误", f"激活失败: {e}", "error")

    def _cancel_selected(self):
        """取消激活选中的批次"""
        if not self.selected_batch_ids:
            return

        count = len(self.selected_batch_ids)
        if not self.show_message("确认", f"确定要取消激活选中的 {count} 个批次吗？", "question"):
            return

        try:
            for batch_id in self.selected_batch_ids:
                self.db_manager.execute_update(
                    "UPDATE batches SET status = ? WHERE id = ?",
                    (STATUS_PENDING, batch_id)
                )
            self._invalidate_scan_cache()  # 使扫码页面缓存失效
            self.refresh()
            self.show_message("成功", f"已取消激活 {count} 个批次", "info")
        except Exception as e:
            self.show_message("错误", f"取消失败: {e}", "error")

    def _archive_selected(self):
        """归档选中的批次"""
        if not self.selected_batch_ids:
            return

        count = len(self.selected_batch_ids)
        if not self.show_message("确认", f"确定要归档选中的 {count} 个批次吗？\n归档后批次将不再显示在活动列表中。", "question"):
            return

        try:
            for batch_id in self.selected_batch_ids:
                self.db_manager.execute_update(
                    "UPDATE batches SET status = ? WHERE id = ?",
                    (STATUS_ARCHIVED, batch_id)
                )
            self._invalidate_scan_cache()  # 使扫码页面缓存失效
            self.refresh()
            self.show_message("成功", f"已归档 {count} 个批次", "info")
        except Exception as e:
            self.show_message("错误", f"归档失败: {e}", "error")

    def _unarchive_selected(self):
        """回档选中的批次"""
        if not self.selected_batch_ids:
            return

        count = len(self.selected_batch_ids)
        if not self.show_message("确认", f"确定要回档选中的 {count} 个批次吗？\n回档后批次将恢复为待激活状态。", "question"):
            return

        try:
            for batch_id in self.selected_batch_ids:
                self.db_manager.execute_update(
                    "UPDATE batches SET status = ? WHERE id = ?",
                    (STATUS_PENDING, batch_id)
                )
            self._invalidate_scan_cache()  # 使扫码页面缓存失效
            self.refresh()
            self.show_message("成功", f"已回档 {count} 个批次", "info")
        except Exception as e:
            self.show_message("错误", f"回档失败: {e}", "error")

    def _edit_selected(self):
        """编辑选中的批次或货柜"""
        if self.selection_type == 'batch':
            # 单选批次 → 编辑单个批次
            batch_id = list(self.selected_batch_ids)[0]
            from ..dialogs.batch_dialogs import BatchEditDialog
            dialog = BatchEditDialog(self.db_manager, batch_id, self)
            if dialog.exec():
                self._invalidate_scan_cache()  # 使扫码页面缓存失效
                self.refresh()

        elif self.selection_type == 'container':
            # 单选货柜 → 编辑货柜下所有批次
            from ..dialogs.batch_dialogs import ContainerEditDialog
            batch_ids = list(self.selected_batch_ids)
            customer_name, container_id = self.selected_container_key
            dialog = ContainerEditDialog(self.db_manager, batch_ids, customer_name, container_id, self)
            if dialog.exec():
                self._invalidate_scan_cache()  # 使扫码页面缓存失效
                self.refresh()

    def _show_detail(self):
        """显示批次详情"""
        if not self.selected_batch_ids:
            return

        from ..dialogs.batch_dialogs import BatchDetailDialog
        dialog = BatchDetailDialog(self.db_manager, list(self.selected_batch_ids), self)
        dialog.exec()

    def _load_batch_params(self):
        """从数据库加载批次创建参数"""
        if not hasattr(self, 'ui_config') or not self.ui_config:
            return

        config = self.ui_config.get_batch_params()
        if config.get('prefix'):
            self.prefix_input.setText(config['prefix'])
        if config.get('start'):
            self.start_input.setText(config['start'])
        if config.get('end'):
            self.end_input.setText(config['end'])
        if config.get('suffix'):
            self.suffix_input.setText(config['suffix'])
        if config.get('container_id'):
            self.container_input.setText(config['container_id'])
        # customer_id 需要在 combo 中查找
        if config.get('customer_id'):
            for i in range(self.customer_combo.count()):
                if self.customer_combo.itemData(i) == config['customer_id']:
                    self.customer_combo.setCurrentIndex(i)
                    break

    def _save_batch_params(self):
        """保存批次创建参数到数据库"""
        if self._loading:
            return
        if not hasattr(self, 'ui_config') or not self.ui_config:
            return

        self.ui_config.set_batch_params(
            prefix=self.prefix_input.text(),
            start=self.start_input.text(),
            end=self.end_input.text(),
            suffix=self.suffix_input.text(),
            container_id=self.container_input.text(),
            customer_id=self.customer_combo.currentData()
        )

    def refresh(self):
        """刷新页面"""
        self._loading = True
        self._load_customers()
        self._load_batch_params()
        self._loading = False
        self._load_batch_list()
        # 更新顶部栏的批次统计
        self._update_topbar_stats()

    def _update_topbar_stats(self):
        """更新顶部栏的批次统计信息"""
        if self.main_window and hasattr(self.main_window, '_update_batch_stats'):
            self.main_window._update_batch_stats()
