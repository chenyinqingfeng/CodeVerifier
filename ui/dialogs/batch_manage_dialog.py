"""
批次管理对话框 - 支持多选删除和筛选
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QCheckBox, QMessageBox, QWidget, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ..styles import Colors, Fonts, Sizes


class BatchManageDialog(QDialog):
    """批次管理对话框"""

    # 批次删除成功信号
    batches_deleted = Signal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        self.setWindowTitle("批次管理")
        self.setMinimumSize(1150, 650)
        self.setModal(True)

        self._setup_ui()
        self._load_filters()
        self._load_batches()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 标题
        title = QLabel("📦 批次管理")
        title.setFont(QFont(Fonts.FAMILY, 16, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        layout.addWidget(title)

        # 筛选区域
        self._setup_filters(layout)

        # 批次表格
        self._setup_table(layout)

        # 底部操作区
        self._setup_actions(layout)

    def _setup_filters(self, parent_layout):
        """设置筛选区域"""
        # 统计栏
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
                padding: 8px 16px;
            }}
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(24)
        stats_layout.setContentsMargins(0, 0, 0, 0)

        # 统计标签
        self.stat_labels = {}
        stat_items = [
            ("total", "全部", Colors.TEXT_PRIMARY_LIGHT),
            ("pending", "待激活", Colors.WARNING),
            ("active", "活动中", Colors.SUCCESS),
            ("archived", "已归档", Colors.TEXT_MUTED_LIGHT),
        ]

        for key, name, color in stat_items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(6)

            name_label = QLabel(f"{name}:")
            name_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
            item_layout.addWidget(name_label)

            count_label = QLabel("0")
            count_label.setFont(QFont(Fonts.FAMILY, 14, QFont.Bold))
            count_label.setStyleSheet(f"color: {color};")
            item_layout.addWidget(count_label)

            self.stat_labels[key] = count_label
            stats_layout.addLayout(item_layout)

        stats_layout.addStretch()
        parent_layout.addWidget(stats_frame)

        # 筛选区域
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
                padding: 12px;
            }}
        """)

        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(16)

        # 客户筛选
        filter_layout.addWidget(QLabel("客户:"))
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(150)
        self.customer_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.customer_combo)

        # 状态筛选
        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.setMinimumWidth(120)
        self.status_combo.addItem("全部状态", -1)
        self.status_combo.addItem("待激活", 0)
        self.status_combo.addItem("活动中", 1)
        self.status_combo.addItem("已归档", 2)
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.status_combo)

        filter_layout.addStretch()

        # 全选/取消全选
        self.select_all_cb = QCheckBox("全选")
        self.select_all_cb.stateChanged.connect(self._on_select_all)
        filter_layout.addWidget(self.select_all_cb)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.clicked.connect(self._load_batches)
        filter_layout.addWidget(refresh_btn)

        parent_layout.addWidget(filter_frame)

    def _setup_table(self, parent_layout):
        """设置批次表格"""
        self.batch_table = QTableWidget()
        self.batch_table.setColumnCount(7)
        self.batch_table.setHorizontalHeaderLabels([
            "选择", "批次名称", "客户", "条码数", "已扫描", "状态", "创建时间"
        ])

        # 设置列宽
        header = self.batch_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)

        self.batch_table.setColumnWidth(0, 50)
        self.batch_table.setColumnWidth(3, 80)
        self.batch_table.setColumnWidth(4, 80)
        self.batch_table.setColumnWidth(5, 80)
        self.batch_table.setColumnWidth(6, 180)

        self.batch_table.verticalHeader().setDefaultSectionSize(40)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.batch_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
                gridline-color: {Colors.BORDER};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND_LIGHT};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: bold;
            }}
        """)

        parent_layout.addWidget(self.batch_table, 1)

    def _setup_actions(self, parent_layout):
        """设置底部操作区"""
        action_frame = QFrame()
        action_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
                padding: 12px;
            }}
        """)

        action_layout = QHBoxLayout(action_frame)

        # 选中计数
        self.selected_label = QLabel("已选择: 0 个批次")
        self.selected_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        action_layout.addWidget(self.selected_label)

        action_layout.addStretch()

        # 取消按钮
        cancel_btn = QPushButton("关闭")
        cancel_btn.setMinimumWidth(80)
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)

        # 删除按钮
        self.delete_btn = QPushButton("删除选中批次")
        self.delete_btn.setMinimumWidth(120)
        self.delete_btn.setMinimumHeight(36)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ERROR};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                font-weight: bold;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
            }}
        """)
        self.delete_btn.clicked.connect(self._on_delete_selected)
        self.delete_btn.setEnabled(False)
        action_layout.addWidget(self.delete_btn)

        parent_layout.addWidget(action_frame)

    def _load_filters(self):
        """加载筛选选项"""
        # 加载客户列表
        self.customer_combo.clear()
        self.customer_combo.addItem("全部客户", None)

        try:
            customers = self.db_manager.get_all_customers()
            for customer in customers:
                self.customer_combo.addItem(
                    customer['customer_name'],
                    customer['id']
                )
        except Exception as e:
            print(f"加载客户列表失败: {e}")

    def _update_stats(self):
        """更新统计数据"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # 总数
                cursor.execute("SELECT COUNT(*) FROM batches")
                total = cursor.fetchone()[0]

                # 待激活 (status=0)
                cursor.execute("SELECT COUNT(*) FROM batches WHERE status = 0")
                pending = cursor.fetchone()[0]

                # 活动中 (status=1)
                cursor.execute("SELECT COUNT(*) FROM batches WHERE status = 1")
                active = cursor.fetchone()[0]

                # 已归档 (status=2)
                cursor.execute("SELECT COUNT(*) FROM batches WHERE status = 2")
                archived = cursor.fetchone()[0]

            self.stat_labels["total"].setText(str(total))
            self.stat_labels["pending"].setText(str(pending))
            self.stat_labels["active"].setText(str(active))
            self.stat_labels["archived"].setText(str(archived))

        except Exception as e:
            print(f"更新统计失败: {e}")

    def _load_batches(self):
        """加载批次数据"""
        self.batch_table.setRowCount(0)
        self.select_all_cb.setChecked(False)
        self._update_stats()  # 更新统计数据

        # 获取筛选条件
        customer_id = self.customer_combo.currentData()
        status = self.status_combo.currentData()

        try:
            # 构建查询
            query = """
                SELECT b.id, b.batch_name, c.customer_name, b.total_count,
                       b.matched_count, b.status, b.created_at, b.customer_id
                FROM batches b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE 1=1
            """
            params = []

            if customer_id is not None:
                query += " AND b.customer_id = ?"
                params.append(customer_id)

            if status != -1:
                query += " AND b.status = ?"
                params.append(status)

            query += " ORDER BY b.created_at DESC"

            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                batches = cursor.fetchall()

            # 填充表格
            self.batch_table.setRowCount(len(batches))

            status_map = {0: "待激活", 1: "活动中", 2: "已归档"}
            status_colors = {0: Colors.WARNING, 1: Colors.SUCCESS, 2: Colors.TEXT_MUTED_LIGHT}

            for row, batch in enumerate(batches):
                batch_id, batch_name, customer_name, total_count, matched_count, status_val, created_at, cust_id = batch

                # 复选框
                checkbox = QCheckBox()
                checkbox.setProperty("batch_id", batch_id)
                checkbox.stateChanged.connect(self._on_checkbox_changed)
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.batch_table.setCellWidget(row, 0, checkbox_widget)

                # 批次名称
                self.batch_table.setItem(row, 1, QTableWidgetItem(batch_name or "-"))

                # 客户
                self.batch_table.setItem(row, 2, QTableWidgetItem(customer_name or "-"))

                # 条码数
                self.batch_table.setItem(row, 3, QTableWidgetItem(str(total_count or 0)))

                # 已扫描
                self.batch_table.setItem(row, 4, QTableWidgetItem(str(matched_count or 0)))

                # 状态
                status_text = status_map.get(status_val, "未知")
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(Qt.GlobalColor.black)
                self.batch_table.setItem(row, 5, status_item)

                # 创建时间
                time_str = str(created_at)[:19] if created_at else "-"
                self.batch_table.setItem(row, 6, QTableWidgetItem(time_str))

            self._update_selected_count()

        except Exception as e:
            print(f"加载批次失败: {e}")
            QMessageBox.warning(self, "错误", f"加载批次失败: {e}")

    def _on_filter_changed(self):
        """筛选条件改变"""
        self._load_batches()

    def _on_select_all(self, state):
        """全选/取消全选"""
        checked = state == 2  # Qt.CheckState.Checked 的值是 2
        for row in range(self.batch_table.rowCount()):
            widget = self.batch_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(checked)

    def _on_checkbox_changed(self):
        """复选框状态改变"""
        self._update_selected_count()

    def _update_selected_count(self):
        """更新选中计数"""
        count = self._get_selected_count()
        self.selected_label.setText(f"已选择: {count} 个批次")
        self.delete_btn.setEnabled(count > 0)

    def _get_selected_count(self) -> int:
        """获取选中数量"""
        count = 0
        for row in range(self.batch_table.rowCount()):
            widget = self.batch_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    count += 1
        return count

    def _get_selected_batch_ids(self) -> list:
        """获取选中的批次ID列表"""
        ids = []
        for row in range(self.batch_table.rowCount()):
            widget = self.batch_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    batch_id = checkbox.property("batch_id")
                    if batch_id:
                        ids.append(batch_id)
        return ids

    def _on_delete_selected(self):
        """删除选中的批次 - 三级确认防误删"""
        batch_ids = self._get_selected_batch_ids()
        if not batch_ids:
            return

        # ========== 第一级确认：你确定要这样做吗？ ==========
        result1 = QMessageBox.warning(
            self,
            "⚠️ 第一步确认",
            f"你确定要删除选中的 {len(batch_ids)} 个批次吗？\n\n"
            "请仔细核对后再继续！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if result1 != QMessageBox.Yes:
            return

        # ========== 第二级确认：这样做会导致什么后果？ ==========
        # 统计将要删除的数据量
        total_barcodes = 0
        total_logs = 0
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                for batch_id in batch_ids:
                    cursor.execute("SELECT COUNT(*) FROM barcodes WHERE batch_id = ?", (batch_id,))
                    total_barcodes += cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM scan_logs WHERE batch_id = ?", (batch_id,))
                    total_logs += cursor.fetchone()[0]
        except:
            pass

        result2 = QMessageBox.critical(
            self,
            "🚨 第二步确认 - 后果警告",
            f"此操作将会导致以下数据被永久删除：\n\n"
            f"• 批次数量：{len(batch_ids)} 个\n"
            f"• 条码数据：{total_barcodes} 条\n"
            f"• 扫描日志：{total_logs} 条\n\n"
            "以上数据删除后将无法恢复！\n"
            "你确定了解后果吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if result2 != QMessageBox.Yes:
            return

        # ========== 第三级确认：最后机会！ ==========
        result3 = QMessageBox.critical(
            self,
            "💀 最后确认 - 不可撤销",
            "这是最后一次确认！\n\n"
            "点击「Yes」后数据将被永久删除，\n"
            "没有任何办法可以恢复！\n\n"
            "你真的、确定、一定要删除吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if result3 != QMessageBox.Yes:
            return

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                for batch_id in batch_ids:
                    # 先删除关联的条码
                    cursor.execute("DELETE FROM barcodes WHERE batch_id = ?", (batch_id,))
                    # 删除关联的扫描日志
                    cursor.execute("DELETE FROM scan_logs WHERE batch_id = ?", (batch_id,))
                    # 删除批次
                    cursor.execute("DELETE FROM batches WHERE id = ?", (batch_id,))

                conn.commit()

            QMessageBox.information(self, "成功", f"已删除 {len(batch_ids)} 个批次")
            self._load_batches()
            # 发出信号通知外部刷新
            self.batches_deleted.emit()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除失败: {e}")
