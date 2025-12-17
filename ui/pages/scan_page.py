"""
扫码验证页面 - 核心功能页面
优化版：使用批次Tab视图 + 高性能表格
"""

from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGraphicsDropShadowEffect, QAbstractItemView,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QColor, QPalette, QPen, QBrush

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


class SelectionColorDelegate(QStyledItemDelegate):
    """自定义委托：处理选中行白色文字和已扫描行淡绿色背景"""

    def paint(self, painter, option, index):
        painter.save()

        # 获取背景色
        bg_brush = index.data(Qt.BackgroundRole)

        if option.state & QStyle.State_Selected:
            # 选中状态：蓝色背景+白色文字
            painter.fillRect(option.rect, QColor(Colors.PRIMARY))
            painter.setPen(QPen(QColor("white")))
        else:
            # 非选中状态：绘制item的背景色（已扫描行的淡绿色）
            if bg_brush:
                painter.fillRect(option.rect, bg_brush.color())
            painter.setPen(QPen(QColor(Colors.TEXT_PRIMARY_LIGHT)))

        # 获取文本和字体
        text = index.data(Qt.DisplayRole) or ""
        font = index.data(Qt.FontRole)
        if font:
            painter.setFont(font)

        # 获取前景色（如果有设置，且非选中状态）
        if not (option.state & QStyle.State_Selected):
            fg_brush = index.data(Qt.ForegroundRole)
            if fg_brush:
                painter.setPen(QPen(fg_brush.color()))

        # 获取对齐方式
        alignment = index.data(Qt.TextAlignmentRole)
        if alignment is None:
            alignment = Qt.AlignVCenter | Qt.AlignLeft

        # 绘制文本（留出padding）
        text_rect = option.rect.adjusted(8, 0, -8, 0)
        painter.drawText(text_rect, alignment, str(text))

        painter.restore()


class ScanResultOverlay(QFrame):
    """扫码结果叠加层 - 大字显示在表格中央，给一线员工远远就能看到"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ScanResultOverlay")
        self._setup_ui()
        self._hide_timer = None
        self.hide()  # 初始隐藏

    def _setup_ui(self):
        """设置UI - 超大面积、超大字体，一线员工远远就能看到"""
        self.setFixedSize(900, 350)  # 超大面积

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 60, 80, 60)
        layout.setAlignment(Qt.AlignCenter)

        # 结果标签 - 超超超大字体
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignCenter)
        # 使用像素大小设置超大字体
        font = QFont("Microsoft YaHei")
        font.setPixelSize(150)  # 150像素超大字！
        font.setBold(True)
        self.result_label.setFont(font)
        layout.addWidget(self.result_label)

    def show_result(self, result_text: str, result_type: str = "success"):
        """
        显示扫码结果，5秒后自动消失

        Args:
            result_text: 结果文本（如"验证通过"、"重复扫码"、"不在活动批次"等）
            result_type: 结果类型（success/warning/error）
        """
        # 取消之前的定时器
        if self._hide_timer:
            self._hide_timer.stop()

        # 根据结果类型设置颜色和emoji
        if result_type == "success":
            bg_color = "#4CAF50"  # 绿色
            emoji = "✅"
        elif result_type == "warning":
            bg_color = "#FF9800"  # 橙色
            emoji = "⚠️"
        else:  # error
            bg_color = "#F44336"  # 红色
            emoji = "❌"

        # 更新样式 - 半透明背景
        self.setStyleSheet(f"""
            QFrame#ScanResultOverlay {{
                background-color: rgba({int(bg_color[1:3], 16)}, {int(bg_color[3:5], 16)}, {int(bg_color[5:7], 16)}, 230);
                border-radius: 25px;
                border: 4px solid white;
            }}
        """)
        self.result_label.setText(f"{emoji} {result_text}")
        self.result_label.setStyleSheet("""
            color: white;
            font-size: 120px;
            font-weight: bold;
            font-family: "Microsoft YaHei";
        """)

        # 居中显示
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = (parent_rect.height() - self.height()) // 2 - 50
            self.move(x, y)

        self.show()
        self.raise_()  # 置顶显示

        # 5秒后自动隐藏
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_overlay)
        self._hide_timer.start(5000)

    def hide_overlay(self):
        """隐藏叠加层"""
        self.hide()


class BatchTabButton(QPushButton):
    """批次Tab按钮"""

    def __init__(self, batch_info: dict, parent=None):
        super().__init__(parent)
        self.batch_info = batch_info
        self._is_active = False
        self._update_text()
        self._apply_style()
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(50)

    def _update_text(self):
        """更新按钮文本"""
        name = self.batch_info.get('batch_name', '')
        matched = self.batch_info.get('matched_count', 0)
        total = self.batch_info.get('total_count', 0)
        self.setText(f"{name}\n({matched}/{total})")

    def _apply_style(self):
        """应用样式"""
        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Sizes.RADIUS_SM}px;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 8px 16px;
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
                    border-radius: {Sizes.RADIUS_SM}px;
                    font-size: 13px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BACKGROUND_LIGHT};
                    border-color: {Colors.PRIMARY};
                }}
            """)

    def set_active(self, active: bool):
        """设置激活状态"""
        self._is_active = active
        self._apply_style()

    def update_stats(self, matched_count: int, total_count: int):
        """更新统计数据"""
        self.batch_info['matched_count'] = matched_count
        self.batch_info['total_count'] = total_count
        self._update_text()


class ScanPage(BasePage):
    """扫码验证页面 - 仅显示批次数据表格"""

    # 信号
    batch_changed = Signal(int)  # 批次切换信号

    def __init__(self, db_manager, ui_config, parent=None):
        self.active_batches = []
        self.current_batch_index = 0
        self.tab_buttons = []
        self.batch_tables = {}  # batch_id -> QTableWidget
        self._data_loaded = False  # 数据是否已加载（用于页面缓存）
        super().__init__(db_manager, ui_config, parent)

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Sizes.SPACING_LG, Sizes.SPACING_LG,
                                  Sizes.SPACING_LG, Sizes.SPACING_LG)
        layout.setSpacing(Sizes.SPACING_SM)

        # 批次Tab标签栏
        self._setup_tab_bar(layout)

        # 内容区域（表格）
        self._setup_content_area(layout)

        # 扫码结果叠加层
        self.result_overlay = ScanResultOverlay(self)

    def _setup_tab_bar(self, parent_layout):
        """设置Tab标签栏"""
        self.tab_bar = QFrame()
        self.tab_bar.setFixedHeight(60)
        self.tab_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)

        self.tab_layout = QHBoxLayout(self.tab_bar)
        self.tab_layout.setContentsMargins(10, 5, 10, 5)
        self.tab_layout.setSpacing(10)

        # 添加弹性空间，让Tab按钮均匀分布
        self.tab_layout.addStretch()

        parent_layout.addWidget(self.tab_bar)

    def _setup_content_area(self, parent_layout):
        """设置内容区域"""
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)

        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # 空状态提示
        self.empty_label = QLabel("暂无活动批次\n请到批次管理页面创建或激活批次")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG))
        self.empty_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT}; padding: 100px;")
        self.content_layout.addWidget(self.empty_label)

        parent_layout.addWidget(self.content_frame)

    def _create_batch_table(self, batch_id: int) -> QTableWidget:
        """创建批次条码表格"""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "序号", "客户", "货柜", "生产条码", "是否扫码", "扫码时间", "重复扫码"
        ])
        table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁止编辑

        # 设置表头样式
        header = table.horizontalHeader()
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

        # 列宽设置
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 序号
        table.setColumnWidth(0, 70)
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # 客户
        table.setColumnWidth(1, 70)
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # 货柜
        table.setColumnWidth(2, 110)
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # 条码
        table.setColumnWidth(3, 320)
        header.setSectionResizeMode(4, QHeaderView.Fixed)  # 是否扫码
        table.setColumnWidth(4, 80)
        header.setSectionResizeMode(5, QHeaderView.Fixed)  # 扫码时间
        table.setColumnWidth(5, 350)
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # 重复扫码 - 填充剩余空间

        # 表格样式 - 不设置item背景色，让代码控制
        table.setStyleSheet(f"""
            QTableWidget {{
                border: none;
                gridline-color: {Colors.BORDER};
                font-size: {Fonts.SIZE_SM}px;
                selection-background-color: {Colors.PRIMARY};
                selection-color: white;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)

        table.setAlternatingRowColors(False)  # 关闭交替行颜色，手动设置已扫描行背景
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(50)  # 设置默认行高
        table.setShowGrid(False)

        # 设置自定义委托，确保选中行文字为白色
        table.setItemDelegate(SelectionColorDelegate(table))

        return table

    def load_active_batches(self):
        """从数据库加载活动批次"""
        try:
            # 获取所有活动批次（status=1 表示活动中）
            batches = self.db_manager.execute_query("""
                SELECT
                    b.id,
                    b.batch_name,
                    b.container_id,
                    c.customer_name,
                    b.total_count,
                    b.matched_count
                FROM batches b
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE b.status = 1
                ORDER BY b.created_at DESC
            """)

            self.active_batches = []
            for row in batches:
                self.active_batches.append({
                    'id': row[0],
                    'batch_name': row[1],
                    'container_id': row[2],
                    'customer_name': row[3] or '未指定',
                    'total_count': row[4] or 0,
                    'matched_count': row[5] or 0
                })

            self._refresh_tabs()

        except Exception as e:
            self.set_status(f"加载批次失败: {e}")

    def _refresh_tabs(self):
        """刷新Tab标签栏"""
        # 清空现有Tab按钮
        for btn in self.tab_buttons:
            btn.deleteLater()
        self.tab_buttons.clear()

        # 清空内容区域（保留empty_label）
        for batch_id, table in self.batch_tables.items():
            table.deleteLater()
        self.batch_tables.clear()

        # 移除之前的stretch
        while self.tab_layout.count() > 0:
            item = self.tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 如果没有活动批次
        if not self.active_batches:
            self.empty_label.show()
            self.tab_layout.addStretch()
            return

        self.empty_label.hide()

        # 创建Tab按钮
        for idx, batch in enumerate(self.active_batches):
            tab_btn = BatchTabButton(batch.copy())
            # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
            tab_btn.clicked.connect(partial(self._on_tab_clicked, idx))

            if idx == 0:
                tab_btn.set_active(True)

            self.tab_layout.addWidget(tab_btn)
            self.tab_buttons.append(tab_btn)

        self.tab_layout.addStretch()

        # 为每个批次创建表格
        for idx, batch in enumerate(self.active_batches):
            table = self._create_batch_table(batch['id'])

            if idx == 0:
                self.content_layout.addWidget(table)
                table.show()
            else:
                self.content_layout.addWidget(table)
                table.hide()

            self.batch_tables[batch['id']] = table

            # 加载条码数据
            self._load_batch_data(batch['id'])

        self.current_batch_index = 0

    def _load_batch_data(self, batch_id: int):
        """加载批次条码数据"""
        try:
            barcodes = self.db_manager.execute_query("""
                SELECT
                    bc.id,
                    c.customer_name,
                    b.container_id,
                    bc.barcode,
                    bc.is_matched,
                    bc.scan_time,
                    bc.scan_count
                FROM barcodes bc
                JOIN batches b ON bc.batch_id = b.id
                LEFT JOIN customers c ON b.customer_id = c.id
                WHERE bc.batch_id = ?
                ORDER BY bc.id ASC
            """, (batch_id,))

            table = self.batch_tables.get(batch_id)
            if not table:
                return

            table.setRowCount(len(barcodes))

            for row_idx, row in enumerate(barcodes):
                is_matched = row[4]
                scan_count = row[6] or 0

                # 序号 - 加粗
                item = QTableWidgetItem(str(row_idx + 1))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont(Fonts.FAMILY, 14, QFont.Bold))
                table.setItem(row_idx, 0, item)

                # 客户名称
                item = QTableWidgetItem(row[1] or '')
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_idx, 1, item)

                # 货柜
                item = QTableWidgetItem(row[2] or '')
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_idx, 2, item)

                # 条码 - 加大加粗
                item = QTableWidgetItem(row[3])
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont(Fonts.FAMILY_MONO, 28, QFont.Bold))
                table.setItem(row_idx, 3, item)

                # 是否扫码
                if is_matched:
                    status_text = "✓ 已扫"
                    status_color = Colors.SUCCESS
                else:
                    status_text = "未扫"
                    status_color = Colors.TEXT_MUTED_LIGHT

                item = QTableWidgetItem(status_text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(status_color))
                item.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
                table.setItem(row_idx, 4, item)

                # 扫码时间
                scan_time = row[5] or '-'
                item = QTableWidgetItem(str(scan_time))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont(Fonts.FAMILY_MONO, 24, QFont.Bold))
                table.setItem(row_idx, 5, item)

                # 重复扫码次数
                repeat_text = str(scan_count) if scan_count > 0 else '-'
                item = QTableWidgetItem(repeat_text)
                item.setTextAlignment(Qt.AlignCenter)
                if scan_count > 1:
                    item.setForeground(QColor(Colors.WARNING))
                    item.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
                table.setItem(row_idx, 6, item)

                # 设置已扫描行的护眼淡绿色背景和深绿色文字（整行）
                if is_matched:
                    row_brush = QBrush(QColor("#e8f5e9"))  # 淡绿色背景
                    text_color = QColor("#2e7d32")         # 深绿色/军绿色文字
                    for col in range(7):
                        cell = table.item(row_idx, col)
                        if cell:
                            cell.setBackground(row_brush)
                            # 重复扫码列(col=6)保持独立规则，其他列设置绿色文字
                            if col != 6:
                                cell.setForeground(text_color)

        except Exception as e:
            self.set_status(f"加载条码数据失败: {e}")

    def _on_tab_clicked(self, tab_index: int, checked: bool = False):
        """Tab按钮点击事件处理（兼容 Cython 编译）"""
        self._switch_tab(tab_index)

    def _switch_tab(self, tab_index: int):
        """切换Tab"""
        if tab_index < 0 or tab_index >= len(self.active_batches):
            return

        # 更新按钮状态
        for idx, btn in enumerate(self.tab_buttons):
            btn.set_active(idx == tab_index)

        # 切换显示的表格
        for batch_id, table in self.batch_tables.items():
            table.hide()

        target_batch = self.active_batches[tab_index]
        target_table = self.batch_tables.get(target_batch['id'])
        if target_table:
            target_table.show()

        self.current_batch_index = tab_index
        self.batch_changed.emit(target_batch['id'])

    def refresh_current_batch(self):
        """刷新当前批次的数据"""
        if self.active_batches and 0 <= self.current_batch_index < len(self.active_batches):
            batch = self.active_batches[self.current_batch_index]
            self._load_batch_data(batch['id'])

    def update_tab_stats(self, batch_id: int, matched_count: int, total_count: int):
        """更新Tab按钮上的统计数据"""
        for idx, batch in enumerate(self.active_batches):
            if batch['id'] == batch_id:
                batch['matched_count'] = matched_count
                batch['total_count'] = total_count
                if idx < len(self.tab_buttons):
                    self.tab_buttons[idx].update_stats(matched_count, total_count)
                break

    def show_scan_result(self, result_text: str, result_type: str):
        """显示扫码结果叠加层"""
        self.result_overlay.show_result(result_text, result_type)

    def locate_barcode(self, batch_id: int, barcode: str):
        """定位并高亮显示指定条码"""
        # 切换到对应批次
        for idx, batch in enumerate(self.active_batches):
            if batch['id'] == batch_id:
                if idx != self.current_batch_index:
                    self._switch_tab(idx)
                break

        # 查找并选中条码，滚动到中央显示
        table = self.batch_tables.get(batch_id)
        if table:
            for row in range(table.rowCount()):
                item = table.item(row, 3)  # 条码列
                if item and item.text() == barcode:
                    table.selectRow(row)
                    table.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                    break

    def get_current_batch_id(self) -> int:
        """获取当前批次ID"""
        if self.active_batches and 0 <= self.current_batch_index < len(self.active_batches):
            return self.active_batches[self.current_batch_index]['id']
        return None

    def resizeEvent(self, event):
        """窗口大小改变时重新定位叠加层"""
        super().resizeEvent(event)
        if self.result_overlay.isVisible():
            parent_rect = self.rect()
            x = (parent_rect.width() - self.result_overlay.width()) // 2
            y = (parent_rect.height() - self.result_overlay.height()) // 2 - 50
            self.result_overlay.move(x, y)

    def refresh(self):
        """刷新页面（切换到此页面时调用，已加载数据则跳过）"""
        if not self._data_loaded:
            self.load_active_batches()
            self._data_loaded = True

    def force_refresh(self):
        """强制刷新页面（手动刷新或批次变更时调用）"""
        self._data_loaded = False
        self.load_active_batches()
        self._data_loaded = True

    def invalidate_cache(self):
        """使缓存失效（批次变更时调用，下次切换到此页面会重新加载）"""
        self._data_loaded = False

    def refresh_batch_data(self, batch_id: int):
        """刷新指定批次的表格数据（扫码成功后调用）"""
        if batch_id in self.batch_tables:
            self._load_batch_data(batch_id)
            # 同时更新Tab按钮上的统计
            self._update_batch_stats(batch_id)

    def _update_batch_stats(self, batch_id: int):
        """更新批次统计信息"""
        try:
            result = self.db_manager.execute_query("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_matched = 1 THEN 1 ELSE 0 END) as matched
                FROM barcodes WHERE batch_id = ?
            """, (batch_id,))
            if result:
                total = result[0][0] or 0
                matched = result[0][1] or 0
                self.update_tab_stats(batch_id, matched, total)
        except Exception as e:
            print(f"[ERROR] 更新批次统计失败: {e}")

    # ==================== 扫码状态更新方法 ====================

    def _get_main_window(self):
        """获取主窗口引用"""
        return self.main_window if hasattr(self, 'main_window') else None

    def update_front_status(self, barcode: str, status: str = "success"):
        """更新正面扫码状态"""
        main = self._get_main_window()
        if not main or not hasattr(main, 'front_scan_status'):
            return
        if status == "success":
            main.front_scan_status.setText(barcode)
            main.front_scan_status.setStyleSheet(f"color: {Colors.SUCCESS};")
        elif status == "waiting":
            main.front_scan_status.setText("等待扫码")
            main.front_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        else:
            main.front_scan_status.setText(barcode)
            main.front_scan_status.setStyleSheet(f"color: {Colors.ERROR};")

    def update_back_status(self, barcode: str, status: str = "success"):
        """更新反面扫码状态"""
        main = self._get_main_window()
        if not main or not hasattr(main, 'back_scan_status'):
            return
        if status == "success":
            main.back_scan_status.setText(barcode)
            main.back_scan_status.setStyleSheet(f"color: {Colors.SUCCESS};")
        elif status == "waiting":
            main.back_scan_status.setText("等待扫码")
            main.back_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        else:
            main.back_scan_status.setText(barcode)
            main.back_scan_status.setStyleSheet(f"color: {Colors.ERROR};")

    def update_result_status(self, result: str, status: str = "success"):
        """更新结果状态"""
        main = self._get_main_window()
        if not main or not hasattr(main, 'result_scan_status'):
            return
        main.result_scan_status.setText(result)
        if status == "success":
            main.result_scan_status.setStyleSheet(f"color: {Colors.SUCCESS};")
        elif status == "warning":
            main.result_scan_status.setStyleSheet(f"color: {Colors.WARNING};")
        elif status == "waiting":
            main.result_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        else:
            main.result_scan_status.setStyleSheet(f"color: {Colors.ERROR};")

    def reset_scan_status(self):
        """重置所有扫码状态"""
        main = self._get_main_window()
        if not main:
            return
        if hasattr(main, 'front_scan_status'):
            main.front_scan_status.setText("等待扫码")
            main.front_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        if hasattr(main, 'back_scan_status'):
            main.back_scan_status.setText("等待扫码")
            main.back_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        if hasattr(main, 'result_scan_status'):
            main.result_scan_status.setText("等待扫码")
            main.result_scan_status.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
