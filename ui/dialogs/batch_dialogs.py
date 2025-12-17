"""
批次编辑和详情对话框
"""

import re
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFormLayout, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from ..styles import Colors, Fonts, Sizes


class BatchEditDialog(QDialog):
    """批次编辑对话框"""

    def __init__(self, db_manager, batch_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.batch_id = batch_id
        self.batch_info = None

        self.setWindowTitle("编辑批次")
        self.setFixedSize(450, 320)
        self.setModal(True)

        if self._load_batch_info():
            self._setup_ui()
        else:
            QMessageBox.warning(self, "错误", "无法加载批次信息")
            self.reject()

    def _load_batch_info(self) -> bool:
        """加载批次信息"""
        try:
            result = self.db_manager.execute_query("""
                SELECT b.batch_name, b.container_id, c.customer_name, b.total_count, b.customer_id
                FROM batches b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.id = ?
            """, (self.batch_id,))

            if not result:
                return False

            batch_name, container_id, customer_name, total_count, customer_id = result[0]

            # 获取第一个和最后一个条码
            first = self.db_manager.execute_query("""
                SELECT barcode FROM barcodes WHERE batch_id = ? ORDER BY barcode ASC LIMIT 1
            """, (self.batch_id,))

            last = self.db_manager.execute_query("""
                SELECT barcode FROM barcodes WHERE batch_id = ? ORDER BY barcode DESC LIMIT 1
            """, (self.batch_id,))

            if not first or not last:
                return False

            first_barcode = first[0][0]
            last_barcode = last[0][0]

            # 解析条码格式
            match = re.match(r'^([^\d]*)(\d+)(.*)$', first_barcode)
            if not match:
                return False
            prefix, start_num, suffix = match.groups()

            match_last = re.match(r'^([^\d]*)(\d+)(.*)$', last_barcode)
            if not match_last:
                return False
            _, end_num, _ = match_last.groups()

            self.batch_info = {
                'batch_name': batch_name,
                'container_id': container_id or '',
                'customer_name': customer_name or '未指定',
                'customer_id': customer_id,
                'prefix': prefix,
                'start_num': start_num,
                'end_num': end_num,
                'suffix': suffix,
                'total_count': total_count
            }
            return True

        except Exception as e:
            print(f"[ERROR] 加载批次信息失败: {e}")
            return False

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title = QLabel(f"编辑批次 - {self.batch_info['batch_name']}")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 表单
        form = QFormLayout()
        form.setSpacing(12)

        # 客户选择（可修改）
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumHeight(36)
        self._load_customers()
        form.addRow("客户:", self.customer_combo)

        # 货柜号（可修改）
        self.container_input = QLineEdit(self.batch_info['container_id'])
        self.container_input.setMinimumHeight(36)
        form.addRow("货柜号:", self.container_input)

        # 条码范围（只读显示）
        barcode_range = QLabel(f"{self.batch_info['prefix']}{self.batch_info['start_num']}{self.batch_info['suffix']} ~ {self.batch_info['prefix']}{self.batch_info['end_num']}{self.batch_info['suffix']}")
        barcode_range.setMinimumHeight(36)
        barcode_range.setFont(QFont(Fonts.FAMILY_MONO, Fonts.SIZE_SM))
        barcode_range.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; padding: 8px; background-color: {Colors.BACKGROUND_LIGHT}; border-radius: 4px;")
        form.addRow("条码范围:", barcode_range)

        # 条码数量（只读显示）
        count_label = QLabel(f"{self.batch_info['total_count']} 条")
        count_label.setMinimumHeight(36)
        count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; padding: 8px;")
        form.addRow("条码数量:", count_label)

        layout.addLayout(form)

        # 提示信息
        info = QLabel("提示：条码一旦生成无法修改，只能修改客户和货柜号")
        info.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        info.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT}; padding: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumSize(100, 40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存修改")
        save_btn.setMinimumSize(100, 40)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        save_btn.clicked.connect(self._save_changes)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_customers(self):
        """加载客户列表"""
        self.customer_combo.addItem("未指定", None)
        try:
            customers = self.db_manager.get_all_customers()
            current_index = 0
            for i, customer in enumerate(customers):
                self.customer_combo.addItem(customer['customer_name'], customer['id'])
                if customer['id'] == self.batch_info['customer_id']:
                    current_index = i + 1
            self.customer_combo.setCurrentIndex(current_index)
        except Exception as e:
            print(f"[ERROR] 加载客户列表失败: {e}")

    def _save_changes(self):
        """保存修改 - 只更新客户和货柜号"""
        container_id = self.container_input.text().strip() or None
        customer_id = self.customer_combo.currentData()

        try:
            # 只更新客户和货柜号，不动条码
            self.db_manager.execute_update("""
                UPDATE batches SET
                    container_id = ?,
                    customer_id = ?
                WHERE id = ?
            """, (container_id, customer_id, self.batch_id))

            QMessageBox.information(self, "成功", "批次信息已更新！")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"修改失败！\n\n{str(e)}")


class ContainerEditDialog(QDialog):
    """货柜编辑对话框 - 批量编辑货柜下所有批次"""

    def __init__(self, db_manager, batch_ids: List[int], customer_name: str, container_id: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.batch_ids = batch_ids
        self.old_customer_name = customer_name
        self.old_container_id = container_id

        self.setWindowTitle("编辑货柜")
        self.setFixedSize(450, 300)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        title = QLabel(f"编辑货柜 - {self.old_container_id}")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 表单
        form = QFormLayout()
        form.setSpacing(12)

        # 客户选择
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumHeight(36)
        self._load_customers()
        form.addRow("客户:", self.customer_combo)

        # 货柜号
        self.container_input = QLineEdit(self.old_container_id)
        self.container_input.setMinimumHeight(36)
        form.addRow("货柜号:", self.container_input)

        # 批次数量（只读）
        count_label = QLabel(f"{len(self.batch_ids)} 个批次")
        count_label.setMinimumHeight(36)
        count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; padding: 8px;")
        form.addRow("包含批次:", count_label)

        layout.addLayout(form)

        # 提示信息
        info = QLabel("提示：修改后，该货柜下所有批次的客户和货柜号都会更新")
        info.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        info.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT}; padding: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumSize(100, 40)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存修改")
        save_btn.setMinimumSize(100, 40)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        save_btn.clicked.connect(self._save_changes)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_customers(self):
        """加载客户列表"""
        self.customer_combo.addItem("未指定", None)
        try:
            customers = self.db_manager.get_all_customers()
            current_index = 0
            for i, customer in enumerate(customers):
                self.customer_combo.addItem(customer['customer_name'], customer['id'])
                if customer['customer_name'] == self.old_customer_name:
                    current_index = i + 1
            self.customer_combo.setCurrentIndex(current_index)
        except Exception as e:
            print(f"[ERROR] 加载客户列表失败: {e}")

    def _save_changes(self):
        """保存修改 - 批量更新所有批次"""
        container_id = self.container_input.text().strip() or None
        customer_id = self.customer_combo.currentData()

        try:
            # 批量更新所有批次
            for batch_id in self.batch_ids:
                self.db_manager.execute_update("""
                    UPDATE batches SET
                        container_id = ?,
                        customer_id = ?
                    WHERE id = ?
                """, (container_id, customer_id, batch_id))

            QMessageBox.information(self, "成功", f"已更新 {len(self.batch_ids)} 个批次！")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"修改失败！\n\n{str(e)}")


class BatchDetailDialog(QDialog):
    """批次详情对话框"""

    def __init__(self, db_manager, batch_ids: List[int], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.batch_ids = batch_ids

        self.setWindowTitle("批次详情")
        self.resize(1100, 650)
        self.setModal(True)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题栏
        header = QHBoxLayout()

        self.title_label = QLabel("批次详情")
        self.title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        header.addWidget(self.title_label)

        header.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setMinimumSize(80, 36)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "所属客户", "所属货柜", "生产条码", "是否扫码", "扫码时间", "重复扫码次数", "是否打印", "打印时间"
        ])

        # 表头样式
        header = self.table.horizontalHeader()
        header.setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                font-weight: bold;
                padding: 10px;
                border: none;
                border-bottom: 2px solid {Colors.BORDER};
            }}
        """)

        # 列宽
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 80)      # 所属客户
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 120)     # 所属货柜
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # 生产条码
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 70)      # 是否扫码
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 180)     # 扫码时间
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 100)     # 重复扫码次数
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 70)      # 是否打印
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 180)     # 打印时间

        # 表格样式
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE_LIGHT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Sizes.RADIUS_MD}px;
                gridline-color: {Colors.BORDER};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁止编辑
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

        # 统计信息
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.stats_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        layout.addWidget(self.stats_label)

    def _load_data(self):
        """加载数据"""
        try:
            # 获取批次名称
            batch_names = []
            for batch_id in self.batch_ids:
                result = self.db_manager.execute_query(
                    "SELECT batch_name FROM batches WHERE id = ?", (batch_id,)
                )
                if result:
                    batch_names.append(result[0][0])

            # 更新标题
            if len(self.batch_ids) == 1:
                self.title_label.setText(f"批次详情 - {batch_names[0]}")
            else:
                self.title_label.setText(f"批次详情 - {len(self.batch_ids)}个批次")

            # 加载条码数据
            all_data = []
            for batch_id in self.batch_ids:
                rows = self.db_manager.execute_query("""
                    SELECT
                        c.customer_name,
                        b.container_id,
                        bc.barcode,
                        bc.is_matched,
                        bc.scan_time,
                        bc.is_printed,
                        bc.last_print_time,
                        bc.scan_count
                    FROM barcodes bc
                    JOIN batches b ON bc.batch_id = b.id
                    LEFT JOIN customers c ON b.customer_id = c.id
                    WHERE bc.batch_id = ?
                    ORDER BY bc.id ASC
                """, (batch_id,))
                all_data.extend(rows)

            # 自然排序
            def natural_sort_key(row):
                barcode = row[2]
                parts = re.split(r'(\d+)', barcode)
                return [int(p) if p.isdigit() else p.lower() for p in parts]

            all_data.sort(key=natural_sort_key)

            # 填充表格
            self.table.setRowCount(len(all_data))
            scanned_count = 0
            printed_count = 0

            for row_idx, row in enumerate(all_data):
                customer_name, container_id, barcode, is_matched, scan_time, is_printed, print_time, scan_count = row
                scan_count = scan_count or 0

                # 0: 所属客户
                item = QTableWidgetItem(customer_name or '')
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 0, item)

                # 1: 所属货柜
                item = QTableWidgetItem(container_id or '')
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 1, item)

                # 2: 生产条码
                item = QTableWidgetItem(barcode)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont(Fonts.FAMILY_MONO, Fonts.SIZE_SM))
                self.table.setItem(row_idx, 2, item)

                # 3: 是否扫码
                if is_matched:
                    scanned_count += 1
                    status_text = "✓ 已扫"
                    status_color = Colors.SUCCESS
                else:
                    status_text = "未扫"
                    status_color = Colors.TEXT_MUTED_LIGHT

                item = QTableWidgetItem(status_text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(status_color))
                self.table.setItem(row_idx, 3, item)

                # 4: 扫码时间
                item = QTableWidgetItem(str(scan_time) if scan_time else '-')
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 4, item)

                # 5: 重复扫码次数
                scan_count_text = str(scan_count) if scan_count > 0 else '-'
                item = QTableWidgetItem(scan_count_text)
                item.setTextAlignment(Qt.AlignCenter)
                if scan_count > 1:
                    item.setForeground(QColor(Colors.WARNING))
                    item.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
                self.table.setItem(row_idx, 5, item)

                # 6: 是否打印
                if is_printed:
                    printed_count += 1
                    print_status = "✓ 已打印"
                    print_color = Colors.SUCCESS
                else:
                    print_status = "未打印"
                    print_color = Colors.TEXT_MUTED_LIGHT

                item = QTableWidgetItem(print_status)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(print_color))
                self.table.setItem(row_idx, 6, item)

                # 7: 打印时间
                item = QTableWidgetItem(str(print_time) if print_time else '-')
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 7, item)

                # 已扫描行绿色背景
                if is_matched:
                    row_color = QColor("#e8f5e9")
                    for col in range(8):
                        cell = self.table.item(row_idx, col)
                        if cell:
                            cell.setBackground(row_color)

            # 更新统计信息
            total = len(all_data)
            self.stats_label.setText(
                f"共 {total} 条记录 | 已扫码: {scanned_count} ({scanned_count*100//total if total else 0}%) | "
                f"已打印: {printed_count} ({printed_count*100//total if total else 0}%)"
            )

        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载数据失败！\n\n{str(e)}")
