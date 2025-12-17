"""
条码打印设置页面
提供条码打印参数配置功能

移植自老版本ctk的条码打印页面，支持：
- 真实条码预览（使用python-barcode生成）
- 条码参数配置
- 手动打印和测试打印
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QLineEdit, QFormLayout,
    QCheckBox, QGroupBox, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer, QByteArray, QBuffer
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QPixmap, QImage

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes, NoWheelSpinBox, NoWheelDoubleSpinBox, NoWheelComboBox
from core.barcode_printer import BarcodePrinter, barcode_printer, generate_barcode_image_simple, PIL_AVAILABLE

# PIL图像转换支持
try:
    from PIL import Image
    import io
except ImportError:
    Image = None


class BarcodePreviewWidget(QFrame):
    """条码预览组件（移植自老版本ctk，支持真实条码图像显示）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 150)
        self.barcode_text = ""
        self.label_width = 70  # mm
        self.label_height = 20  # mm
        self.barcode_type = "CODE39"
        self._barcode_printer: BarcodePrinter = None
        self._pil_image = None  # 缓存PIL图像
        self._qt_pixmap = None  # 缓存Qt图像
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 1px solid {Colors.BORDER};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)

    def set_barcode_printer(self, printer: BarcodePrinter):
        """设置条码打印器（用于生成真实条码）"""
        self._barcode_printer = printer

    def set_barcode(self, text: str):
        """设置要预览的条码"""
        self.barcode_text = text
        self._generate_barcode_image()
        self.update()

    def set_label_size(self, width: float, height: float):
        """设置标签尺寸"""
        self.label_width = width
        self.label_height = height
        self._generate_barcode_image()
        self.update()

    def set_barcode_type(self, barcode_type: str):
        """设置条码类型"""
        self.barcode_type = barcode_type
        self._generate_barcode_image()
        self.update()

    def _generate_barcode_image(self):
        """生成真实条码图像"""
        self._pil_image = None
        self._qt_pixmap = None

        if not self.barcode_text:
            return

        try:
            # 优先使用 barcode_printer 生成完整条码图像
            if self._barcode_printer:
                preview_dpi = 200
                pil_image = self._barcode_printer.generate_barcode_image(
                    self.barcode_text,
                    dpi_x=preview_dpi,
                    dpi_y=preview_dpi
                )
            else:
                # 降级方案：使用简化版本
                pil_image = generate_barcode_image_simple(
                    self.barcode_text,
                    barcode_type=self.barcode_type,
                    dpi=150
                )

            if pil_image:
                self._pil_image = pil_image
                self._qt_pixmap = self._pil_to_qpixmap(pil_image)

        except Exception as e:
            print(f"条码预览生成失败: {e}")

    def _pil_to_qpixmap(self, pil_image) -> QPixmap:
        """将PIL图像转换为QPixmap"""
        if pil_image is None or Image is None:
            return None

        try:
            # 确保是RGB模式
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")

            # 转换为QImage
            data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                pil_image.width,
                pil_image.height,
                pil_image.width * 3,
                QImage.Format_RGB888
            )

            return QPixmap.fromImage(qimage)

        except Exception as e:
            print(f"PIL转QPixmap失败: {e}")
            return None

    def paintEvent(self, event):
        """绘制预览"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 计算预览区域
        margin = 30
        available_width = self.width() - 2 * margin
        available_height = self.height() - 2 * margin - 20  # 底部留空显示尺寸

        if self._qt_pixmap and not self._qt_pixmap.isNull():
            # ========== 显示真实条码图像 ==========
            pixmap = self._qt_pixmap

            # 计算缩放比例（保持原始宽高比）
            scale = min(
                available_width / pixmap.width(),
                available_height / pixmap.height()
            )

            display_width = int(pixmap.width() * scale)
            display_height = int(pixmap.height() * scale)

            # 居中定位
            x = (self.width() - display_width) // 2
            y = (self.height() - display_height - 20) // 2

            # 绘制阴影
            shadow_offset = 3
            painter.fillRect(
                x + shadow_offset, y + shadow_offset,
                display_width, display_height,
                QColor("#D0D0D0")
            )

            # 绘制白色背景边框
            painter.setPen(QPen(QColor("black"), 2))
            painter.fillRect(x, y, display_width, display_height, QColor("white"))
            painter.drawRect(x, y, display_width, display_height)

            # 绘制条码图像
            target_rect = painter.viewport()
            scaled_pixmap = pixmap.scaled(
                display_width, display_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            painter.drawPixmap(x, y, scaled_pixmap)

            # 显示尺寸信息
            size_text = f"{self.label_width}mm × {self.label_height}mm"
            painter.setPen(QColor("#666666"))
            font = QFont(Fonts.FAMILY, 9)
            painter.setFont(font)
            painter.drawText(
                0, y + display_height + 5,
                self.width(), 20,
                Qt.AlignCenter,
                size_text
            )

        elif self.barcode_text:
            # ========== 降级：绘制模拟条码 ==========
            scale_x = available_width / self.label_width
            scale_y = available_height / self.label_height
            scale = min(scale_x, scale_y) * 0.8

            label_w = self.label_width * scale
            label_h = self.label_height * scale
            label_x = (self.width() - label_w) / 2
            label_y = (self.height() - label_h - 20) / 2

            # 阴影
            painter.fillRect(
                int(label_x + 3), int(label_y + 3),
                int(label_w), int(label_h),
                QColor("#D0D0D0")
            )

            # 标签背景
            painter.fillRect(int(label_x), int(label_y), int(label_w), int(label_h), QColor("white"))
            painter.setPen(QPen(QColor("black"), 2))
            painter.drawRect(int(label_x), int(label_y), int(label_w), int(label_h))

            # 模拟条码
            barcode_y = label_y + label_h * 0.15
            barcode_h = label_h * 0.5
            barcode_w = label_w * 0.8
            barcode_x = label_x + (label_w - barcode_w) / 2

            bar_count = len(self.barcode_text) * 8
            bar_width = barcode_w / max(1, bar_count)

            for i in range(bar_count):
                if i % 2 == 0:
                    painter.fillRect(
                        int(barcode_x + i * bar_width),
                        int(barcode_y),
                        max(1, int(bar_width * 0.8)),
                        int(barcode_h),
                        QColor("black")
                    )

            # 条码文本
            text_y = barcode_y + barcode_h + label_h * 0.08
            font = QFont(Fonts.FAMILY_MONO, int(8 * scale / 3))
            painter.setFont(font)
            painter.setPen(QColor("black"))
            painter.drawText(
                int(label_x), int(text_y),
                int(label_w), int(label_h * 0.25),
                Qt.AlignCenter,
                self.barcode_text
            )

            # 尺寸信息
            size_text = f"{self.label_width}mm × {self.label_height}mm"
            painter.setPen(QColor("#666666"))
            font = QFont(Fonts.FAMILY, 9)
            painter.setFont(font)
            painter.drawText(
                int(label_x), int(label_y + label_h + 5),
                int(label_w), 20,
                Qt.AlignCenter,
                size_text
            )

        else:
            # ========== 无条码时显示提示 ==========
            painter.setPen(QColor(Colors.TEXT_MUTED_LIGHT))
            font = QFont(Fonts.FAMILY, 12)
            painter.setFont(font)
            painter.drawText(
                0, 0,
                self.width(), self.height(),
                Qt.AlignCenter,
                "输入条码预览"
            )


class PrintPage(BasePage):
    """条码打印设置页面（移植自老版本ctk）"""

    def __init__(self, db_manager, ui_config, parent=None):
        self._loading = True
        self._barcode_printer: BarcodePrinter = None
        self._save_timer = None  # 防抖定时器
        self._current_recipe_id = 1  # 当前配方ID
        super().__init__(db_manager, ui_config, parent)
        self._init_barcode_printer()
        # 初始化完成后加载配置
        self.refresh()
        self._loading = False

    def _init_barcode_printer(self):
        """初始化条码打印器（使用全局单例）"""
        try:
            # 使用全局单例，确保与scan_controller共享同一实例
            self._barcode_printer = barcode_printer
            self._barcode_printer._ui_config = self.ui_config
            self._barcode_printer._load_config()
            self._barcode_printer.set_log_callback(self._log)
            # 连接到预览组件
            if hasattr(self, 'preview_widget'):
                self.preview_widget.set_barcode_printer(self._barcode_printer)
        except Exception as e:
            self._log(f"[ERROR] 初始化条码打印器失败: {e}")

    def _log(self, message: str):
        """日志输出"""
        print(message)
        if hasattr(self, 'set_status'):
            # 移除日志级别前缀用于状态栏显示
            display_msg = message
            for prefix in ['[OK] ', '[INFO] ', '[WARN] ', '[ERROR] ']:
                if display_msg.startswith(prefix):
                    display_msg = display_msg[len(prefix):]
                    break
            self.set_status(display_msg)

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Sizes.SPACING_LG, Sizes.SPACING_LG,
                                  Sizes.SPACING_LG, Sizes.SPACING_LG)
        layout.setSpacing(Sizes.SPACING_MD)

        # 左侧设置面板（带滚动条）
        self._setup_settings_panel(layout)

        # 右侧预览面板
        self._setup_preview_panel(layout)

    def _setup_settings_panel(self, parent_layout):
        """设置左侧设置面板（带滚动条）"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setFixedWidth(420)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.SURFACE_LIGHT};
                border: none;
                border-radius: {Sizes.RADIUS_LG}px;
            }}
            QScrollBar:vertical {{
                background: {Colors.SURFACE_LIGHT};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Colors.TEXT_MUTED_LIGHT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # 内容容器
        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border: none;
            }}
        """)

        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(16, 12, 16, 12)
        settings_layout.setSpacing(8)

        # 标题
        title = QLabel("条码打印设置")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        settings_layout.addWidget(title)

        # 启用开关
        self._setup_enable_section(settings_layout)

        # 打印机设置（全局，不属于配方）
        self._setup_printer_section(settings_layout)

        # 配方管理区域
        self._setup_recipe_section(settings_layout)

        # 条码类型
        self._setup_barcode_type_section(settings_layout)

        # 标签尺寸
        self._setup_label_size_section(settings_layout)

        # 条码参数
        self._setup_barcode_params_section(settings_layout)

        # 文字设置
        self._setup_text_section(settings_layout)

        # 重复打印设置
        self._setup_repeat_section(settings_layout)

        # 添加弹性空间
        settings_layout.addStretch()

        scroll_area.setWidget(settings_frame)
        parent_layout.addWidget(scroll_area)

    def _setup_recipe_section(self, parent_layout):
        """设置配方管理区域"""
        group = QGroupBox("打印配方")
        group.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        group_layout = QHBoxLayout(group)
        group_layout.setSpacing(8)

        # 配方下拉框
        self.recipe_combo = NoWheelComboBox()
        self.recipe_combo.setMinimumHeight(36)
        self.recipe_combo.currentIndexChanged.connect(self._on_recipe_changed)
        group_layout.addWidget(self.recipe_combo, 1)

        # 新建配方按钮
        self.new_recipe_btn = QPushButton("+")
        self.new_recipe_btn.setFixedSize(36, 36)
        self.new_recipe_btn.setToolTip("新建配方（需要管理员权限）")
        self.new_recipe_btn.setCursor(Qt.PointingHandCursor)
        self.new_recipe_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.SUCCESS_DARK};
            }}
        """)
        self.new_recipe_btn.clicked.connect(self._on_new_recipe)
        group_layout.addWidget(self.new_recipe_btn)

        # 删除配方按钮
        self.delete_recipe_btn = QPushButton("×")
        self.delete_recipe_btn.setFixedSize(36, 36)
        self.delete_recipe_btn.setToolTip("删除配方（需要管理员权限）")
        self.delete_recipe_btn.setCursor(Qt.PointingHandCursor)
        self.delete_recipe_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ERROR};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.ERROR_DARK};
            }}
        """)
        self.delete_recipe_btn.clicked.connect(self._on_delete_recipe)
        group_layout.addWidget(self.delete_recipe_btn)

        parent_layout.addWidget(group)

    def _setup_enable_section(self, parent_layout):
        """设置启用开关（两个复选框同一行）"""
        enable_frame = QFrame()
        enable_layout = QHBoxLayout(enable_frame)
        enable_layout.setContentsMargins(0, 0, 0, 0)
        enable_layout.setSpacing(16)

        self.enable_check = QCheckBox("启用打印")
        self.enable_check.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.enable_check.stateChanged.connect(self._on_enable_changed)
        enable_layout.addWidget(self.enable_check)

        self.correction_check = QCheckBox("打印后锁定验证")
        self.correction_check.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.correction_check.setToolTip("启用后，打印成功后必须两把枪都扫到相同条码才能继续")
        self.correction_check.stateChanged.connect(self._on_correction_changed)
        enable_layout.addWidget(self.correction_check)

        enable_layout.addStretch()

        parent_layout.addWidget(enable_frame)

    def _setup_printer_section(self, parent_layout):
        """设置打印机选择"""
        group = QGroupBox("打印机设置")
        group.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        # 打印机选择行
        printer_row = QHBoxLayout()

        self.printer_combo = NoWheelComboBox()
        self.printer_combo.setMinimumHeight(36)
        self.printer_combo.addItem("正在加载打印机列表...")
        self.printer_combo.currentTextChanged.connect(self._on_printer_changed)
        printer_row.addWidget(self.printer_combo, 1)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.clicked.connect(self._refresh_printers)
        printer_row.addWidget(refresh_btn)

        group_layout.addLayout(printer_row)

        parent_layout.addWidget(group)

    def _setup_barcode_type_section(self, parent_layout):
        """设置条码类型"""
        group = QGroupBox("条码类型")
        group.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        group_layout = QVBoxLayout(group)

        self.barcode_type_combo = NoWheelComboBox()
        self.barcode_type_combo.setMinimumHeight(36)
        self.barcode_type_combo.addItems(["CODE39", "CODE128"])
        self.barcode_type_combo.currentTextChanged.connect(self._on_barcode_type_changed)
        group_layout.addWidget(self.barcode_type_combo)

        parent_layout.addWidget(group)

    def _setup_label_size_section(self, parent_layout):
        """设置标签尺寸"""
        group = QGroupBox("标签尺寸 (毫米)")
        group.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        group_layout = QHBoxLayout(group)
        group_layout.setSpacing(16)

        # 宽度
        width_layout = QVBoxLayout()
        width_label = QLabel("宽度")
        width_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        width_layout.addWidget(width_label)

        self.label_width_spin = NoWheelDoubleSpinBox()
        self.label_width_spin.setRange(10, 200)
        self.label_width_spin.setValue(70)
        self.label_width_spin.setSuffix(" mm")
        self.label_width_spin.setMinimumHeight(36)
        self.label_width_spin.valueChanged.connect(self._on_settings_changed)
        width_layout.addWidget(self.label_width_spin)

        group_layout.addLayout(width_layout)

        # 高度
        height_layout = QVBoxLayout()
        height_label = QLabel("高度")
        height_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        height_layout.addWidget(height_label)

        self.label_height_spin = NoWheelDoubleSpinBox()
        self.label_height_spin.setRange(5, 100)
        self.label_height_spin.setValue(20)
        self.label_height_spin.setSuffix(" mm")
        self.label_height_spin.setMinimumHeight(36)
        self.label_height_spin.valueChanged.connect(self._on_settings_changed)
        height_layout.addWidget(self.label_height_spin)

        group_layout.addLayout(height_layout)

        parent_layout.addWidget(group)

    def _setup_barcode_params_section(self, parent_layout):
        """设置条码参数"""
        group = QGroupBox("条码参数")
        group.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        group_layout = QFormLayout(group)
        group_layout.setSpacing(12)

        # 条码宽度
        self.barcode_width_spin = NoWheelDoubleSpinBox()
        self.barcode_width_spin.setRange(0.1, 2.0)
        self.barcode_width_spin.setValue(0.25)
        self.barcode_width_spin.setSingleStep(0.05)
        self.barcode_width_spin.setSuffix(" mm")
        self.barcode_width_spin.setMinimumHeight(36)
        self.barcode_width_spin.valueChanged.connect(self._on_settings_changed)
        group_layout.addRow("条码线宽:", self.barcode_width_spin)

        # 条码高度
        self.barcode_height_spin = NoWheelDoubleSpinBox()
        self.barcode_height_spin.setRange(5, 50)
        self.barcode_height_spin.setValue(10)
        self.barcode_height_spin.setSuffix(" mm")
        self.barcode_height_spin.setMinimumHeight(36)
        self.barcode_height_spin.valueChanged.connect(self._on_settings_changed)
        group_layout.addRow("条码高度:", self.barcode_height_spin)

        # 条码上边距
        self.top_margin_spin = NoWheelDoubleSpinBox()
        self.top_margin_spin.setRange(0, 20)
        self.top_margin_spin.setValue(2.0)
        self.top_margin_spin.setSuffix(" mm")
        self.top_margin_spin.setMinimumHeight(36)
        self.top_margin_spin.valueChanged.connect(self._on_settings_changed)
        group_layout.addRow("上边距:", self.top_margin_spin)

        parent_layout.addWidget(group)

    def _setup_text_section(self, parent_layout):
        """设置文字参数"""
        group = QGroupBox("文字设置")
        group.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        group_layout = QFormLayout(group)
        group_layout.setSpacing(12)

        # 字体大小
        self.font_size_spin = NoWheelSpinBox()
        self.font_size_spin.setRange(6, 24)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setMinimumHeight(36)
        self.font_size_spin.valueChanged.connect(self._on_settings_changed)
        group_layout.addRow("字体大小:", self.font_size_spin)

        # 文字间距
        self.text_gap_spin = NoWheelDoubleSpinBox()
        self.text_gap_spin.setRange(-5, 10)
        self.text_gap_spin.setValue(-1.0)
        self.text_gap_spin.setSuffix(" mm")
        self.text_gap_spin.setMinimumHeight(36)
        self.text_gap_spin.valueChanged.connect(self._on_settings_changed)
        group_layout.addRow("文字间距:", self.text_gap_spin)

        parent_layout.addWidget(group)

    def _setup_repeat_section(self, parent_layout):
        """设置重复打印次数"""
        group = QGroupBox("自动打印设置")
        group.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM, QFont.Bold))
        group_layout = QFormLayout(group)
        group_layout.setSpacing(12)

        # 重复打印次数
        self.repeat_count_spin = NoWheelSpinBox()
        self.repeat_count_spin.setRange(1, 10)
        self.repeat_count_spin.setValue(1)
        self.repeat_count_spin.setSuffix(" 次")
        self.repeat_count_spin.setMinimumHeight(36)
        self.repeat_count_spin.setToolTip("自动打印时重复打印的次数（1-10次）")
        self.repeat_count_spin.valueChanged.connect(self._on_settings_changed)
        group_layout.addRow("重复打印次数:", self.repeat_count_spin)

        parent_layout.addWidget(group)

    def _setup_preview_panel(self, parent_layout):
        """设置右侧预览面板"""
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame#previewFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)
        preview_frame.setObjectName("previewFrame")

        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(20, 20, 20, 20)
        preview_layout.setSpacing(16)

        # 标题行
        header_layout = QHBoxLayout()

        title = QLabel("条码预览")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_LG, QFont.Bold))
        header_layout.addWidget(title)

        # 锁定状态显示
        lock_title = QLabel("锁定:")
        lock_title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        lock_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        lock_title.hide()
        header_layout.addWidget(lock_title)
        self._lock_title_label = lock_title

        self.lock_status_label = QLabel("未锁定")
        self.lock_status_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.lock_status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        self.lock_status_label.hide()  # 默认隐藏，功能启用时显示
        header_layout.addWidget(self.lock_status_label)

        header_layout.addStretch()

        # 手动解锁按钮
        self.manual_unlock_btn = QPushButton("🔓 手动解锁")
        self.manual_unlock_btn.setMinimumHeight(40)
        self.manual_unlock_btn.setCursor(Qt.PointingHandCursor)
        self.manual_unlock_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.WARNING_DARK};
            }}
        """)
        self.manual_unlock_btn.clicked.connect(self._manual_unlock)
        self.manual_unlock_btn.hide()  # 默认隐藏，功能启用且锁定时显示
        header_layout.addWidget(self.manual_unlock_btn)

        # 手动打印按钮
        self.manual_print_btn = QPushButton("🖨 手动打印")
        self.manual_print_btn.setMinimumHeight(40)
        self.manual_print_btn.setCursor(Qt.PointingHandCursor)
        self.manual_print_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        self.manual_print_btn.clicked.connect(self._manual_print)
        header_layout.addWidget(self.manual_print_btn)

        # 测试打印按钮
        self.test_print_btn = QPushButton("🧪 测试打印")
        self.test_print_btn.setMinimumHeight(40)
        self.test_print_btn.setCursor(Qt.PointingHandCursor)
        self.test_print_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_SM}px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.WARNING_DARK};
            }}
        """)
        self.test_print_btn.clicked.connect(self._test_print)
        header_layout.addWidget(self.test_print_btn)

        preview_layout.addLayout(header_layout)

        # 当前打印输入
        input_layout = QHBoxLayout()
        input_label = QLabel("当前条码:")
        input_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        input_layout.addWidget(input_label)

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("输入条码或扫码自动填入")
        self.barcode_input.setMinimumHeight(40)
        self.barcode_input.setFont(QFont(Fonts.FAMILY_MONO, Fonts.SIZE_BASE))
        self.barcode_input.textChanged.connect(self._on_barcode_changed)
        self.barcode_input.returnPressed.connect(self._manual_print)
        input_layout.addWidget(self.barcode_input)

        preview_layout.addLayout(input_layout)

        # 预览区域
        self.preview_widget = BarcodePreviewWidget()
        self.preview_widget.setMinimumHeight(200)
        # 连接条码打印器到预览组件
        if self._barcode_printer:
            self.preview_widget.set_barcode_printer(self._barcode_printer)
        preview_layout.addWidget(self.preview_widget, 1)

        parent_layout.addWidget(preview_frame)

    def _load_config(self):
        """加载打印配置（从配方和全局配置）"""
        try:
            self._loading = True

            # 刷新配方列表
            self._refresh_recipes()

            # 获取当前配方ID并选中
            self._current_recipe_id = self.ui_config.get_current_recipe_id()
            self._select_recipe_in_combo(self._current_recipe_id)

            # 从配方加载参数
            recipe = self.ui_config.get_print_recipe_by_id(self._current_recipe_id)
            if recipe:
                self.barcode_type_combo.setCurrentText(recipe.get('barcode_type', 'CODE39'))
                self.label_width_spin.setValue(recipe.get('label_width', 70))
                self.label_height_spin.setValue(recipe.get('label_height', 20))
                self.barcode_width_spin.setValue(recipe.get('barcode_width', 0.25))
                self.barcode_height_spin.setValue(recipe.get('barcode_height', 10))
                self.top_margin_spin.setValue(recipe.get('barcode_top_margin', 2.0))
                self.font_size_spin.setValue(recipe.get('font_size', 12))
                self.text_gap_spin.setValue(recipe.get('text_gap', -1.0))
                self.repeat_count_spin.setValue(recipe.get('auto_print_repeat_count', 1))

            # 从全局配置加载启用开关、打印机等
            config = self.ui_config.get_print_config()
            self.enable_check.setChecked(config.get('enabled', False))
            self.correction_check.setChecked(self.ui_config.is_print_match_correction_enabled())

            # 恢复当前条码
            current_print = config.get('current_print', '')
            if current_print:
                self.barcode_input.setText(current_print)

            # 设置打印机
            printer_name = config.get('printer_name', '')
            if printer_name:
                index = self.printer_combo.findText(printer_name)
                if index >= 0:
                    self.printer_combo.setCurrentIndex(index)
                if self._barcode_printer:
                    self._barcode_printer.set_selected_printer(printer_name)

            # 同步配置到 barcode_printer
            if self._barcode_printer:
                # 合并配方参数和全局配置
                full_config = {
                    'enabled': config.get('enabled', False),
                    'printer_name': printer_name,
                }
                if recipe:
                    full_config.update({
                        'barcode_type': recipe.get('barcode_type', 'CODE39'),
                        'label_width': recipe.get('label_width', 70),
                        'label_height': recipe.get('label_height', 20),
                        'barcode_width': recipe.get('barcode_width', 0.25),
                        'barcode_height': recipe.get('barcode_height', 10),
                        'barcode_top_margin': recipe.get('barcode_top_margin', 2.0),
                        'font_size': recipe.get('font_size', 12),
                        'text_gap': recipe.get('text_gap', -1.0),
                        'auto_print_repeat_count': recipe.get('auto_print_repeat_count', 1),
                    })
                self._barcode_printer.update_config(full_config)
                self._barcode_printer.set_enabled(config.get('enabled', False))

            self._loading = False
            self._update_preview()
            self._update_lock_status(False, "")

        except Exception as e:
            self._loading = False
            self.set_status(f"加载配置失败: {e}")

    def _save_config(self):
        """保存打印配置（保存到配方和全局配置）"""
        if self._loading:
            return

        try:
            printer_name = self.printer_combo.currentText()
            # 过滤无效的打印机名称
            if printer_name.startswith("未找到") or printer_name.startswith("错误"):
                printer_name = ""

            # 配方参数
            recipe_params = {
                'barcode_type': self.barcode_type_combo.currentText(),
                'label_width': self.label_width_spin.value(),
                'label_height': self.label_height_spin.value(),
                'barcode_width': self.barcode_width_spin.value(),
                'barcode_height': self.barcode_height_spin.value(),
                'barcode_top_margin': self.top_margin_spin.value(),
                'font_size': self.font_size_spin.value(),
                'text_gap': self.text_gap_spin.value(),
                'auto_print_repeat_count': self.repeat_count_spin.value(),
            }

            # 保存配方参数到当前配方
            if self._current_recipe_id:
                self.ui_config.update_print_recipe(self._current_recipe_id, recipe_params)

            # 全局配置（打印机、启用开关、当前条码）
            global_config = {
                'enabled': self.enable_check.isChecked(),
                'printer_name': printer_name,
                'current_print': self.barcode_input.text().strip(),
            }
            self.ui_config.save_print_config(global_config)

            # 同步到 barcode_printer
            if self._barcode_printer:
                full_config = {**global_config, **recipe_params}
                self._barcode_printer.update_config(full_config)
                self._barcode_printer.set_enabled(global_config['enabled'])
                if printer_name:
                    self._barcode_printer.set_selected_printer(printer_name)

        except Exception as e:
            self.set_status(f"保存配置失败: {e}")

    def _refresh_printers(self):
        """刷新打印机列表（使用 BarcodePrinter 的方法）"""
        self.printer_combo.clear()

        try:
            # 使用 BarcodePrinter 的静态方法获取打印机列表
            printers = BarcodePrinter.list_printers()

            if printers:
                self.printer_combo.addItems(printers)

                # 恢复之前选择的打印机
                if self._barcode_printer and self._barcode_printer.get_selected_printer():
                    saved_printer = self._barcode_printer.get_selected_printer()
                    index = self.printer_combo.findText(saved_printer)
                    if index >= 0:
                        self.printer_combo.setCurrentIndex(index)
            else:
                self.printer_combo.addItem("未找到打印机")

        except Exception as e:
            self.printer_combo.addItem(f"错误: {e}")

    def _update_preview(self):
        """更新条码预览"""
        # 同步配置到 barcode_printer
        if self._barcode_printer:
            config = {
                'label_width': self.label_width_spin.value(),
                'label_height': self.label_height_spin.value(),
                'barcode_width': self.barcode_width_spin.value(),
                'barcode_height': self.barcode_height_spin.value(),
                'barcode_top_margin': self.top_margin_spin.value(),
                'text_gap': self.text_gap_spin.value(),
                'font_size': self.font_size_spin.value(),
                'barcode_type': self.barcode_type_combo.currentText(),
            }
            self._barcode_printer.update_config(config)
            # 确保预览组件使用最新的打印器
            self.preview_widget.set_barcode_printer(self._barcode_printer)

        self.preview_widget.set_label_size(
            self.label_width_spin.value(),
            self.label_height_spin.value()
        )
        self.preview_widget.set_barcode_type(self.barcode_type_combo.currentText())
        self.preview_widget.set_barcode(self.barcode_input.text())

    def _on_enable_changed(self, state):
        """启用状态改变"""
        self._save_config()

    def _on_correction_changed(self, state):
        """纠错功能状态改变"""
        enabled = state == Qt.CheckState.Checked.value
        self.ui_config.set_print_match_correction_enabled(enabled)
        self._log(f"[INFO] 打印后锁定验证已{'启用' if enabled else '禁用'}")
        # 更新锁定状态显示（根据功能开关状态）
        self._update_lock_status(False, "")
        # 通知TopBar同步更新（通过scan_controller发信号）
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'scan_controller'):
            main_window.scan_controller.print_lock_changed.emit(False, "")

    def _on_printer_changed(self, text):
        """打印机选择改变"""
        if not self._loading:
            # 同步到 barcode_printer
            if self._barcode_printer and text and not text.startswith("未找到") and not text.startswith("错误"):
                self._barcode_printer.set_selected_printer(text)
            self._save_config()

    def _on_barcode_type_changed(self, text):
        """条码类型改变"""
        if not self._loading:
            self._save_config()
            self._update_preview()

    def _on_barcode_changed(self, text):
        """条码输入改变"""
        self._update_preview()
        # 自动保存当前条码到数据库（防抖：延迟500ms保存）
        if not self._loading:
            if self._save_timer:
                self._save_timer.stop()
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._save_config)
            self._save_timer.start(500)  # 500ms后保存

    def _on_settings_changed(self):
        """设置参数改变"""
        if not self._loading:
            self._save_config()
            self._update_preview()

    def _manual_print(self):
        """手动打印（使用真实打印逻辑，需要2级及以上权限）"""
        barcode = self.barcode_input.text().strip()
        if not barcode:
            self.show_message("提示", "请输入要打印的条码", "warning")
            return

        if not self.enable_check.isChecked():
            self.show_message("提示", "请先启用条码打印功能", "warning")
            return

        if not self._barcode_printer:
            self.show_message("错误", "条码打印器未初始化", "error")
            return

        # 权限检查：需要 admin (2级) 及以上权限
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'auth_manager'):
            auth_manager = main_window.auth_manager
            if not auth_manager.has_permission('admin'):
                # 弹出登录对话框
                from ..dialogs.login_dialog import LoginDialog
                from PySide6.QtWidgets import QDialog
                dialog = LoginDialog(auth_manager, self, required_role='admin')
                if dialog.exec() != QDialog.Accepted:
                    return  # 用户取消登录
                # 登录成功，更新导航栏状态
                if hasattr(main_window, 'sidebar'):
                    main_window.sidebar.update_user_info(auth_manager.get_current_user())

        # 执行真实打印
        self._do_print(barcode)

    def _do_print(self, barcode: str):
        """执行打印操作"""
        try:
            success = self._barcode_printer.print_barcode(barcode, force=True)

            if success:
                self._barcode_printer.last_printed_code = barcode
                self.show_message("成功", f"已打印: {barcode}", "info")
                self.set_status(f"已打印条码: {barcode}")
            else:
                self.show_message("错误", "打印失败，请检查打印机状态", "error")
                self.set_status("打印失败")

        except Exception as e:
            self.show_message("错误", f"打印异常: {e}", "error")
            self.set_status(f"打印异常: {e}")

    def _get_main_window(self):
        """获取主窗口引用"""
        widget = self.parent()
        while widget:
            if widget.__class__.__name__ == 'MainWindow':
                return widget
            widget = widget.parent()
        return None

    def _test_print(self):
        """测试打印（生成与当前打印相同长度的假条码）"""
        # 获取当前输入的条码长度
        current_code = self.barcode_input.text().strip()

        if current_code:
            # 使用当前打印条码的长度
            code_length = len(current_code)
        else:
            # 默认14位
            code_length = 14

        # 生成假条码
        import time
        timestamp = str(int(time.time()) % 10000).zfill(4)
        if code_length <= 4:
            test_barcode = timestamp[:code_length]
        else:
            test_barcode = "TEST" + timestamp + ("1" * (code_length - 8))
            test_barcode = test_barcode[:code_length]

        self.barcode_input.setText(test_barcode)

        if not self.enable_check.isChecked():
            self.show_message("提示", "请先启用条码打印功能", "warning")
            return

        if not self._barcode_printer:
            self.show_message("错误", "条码打印器未初始化", "error")
            return

        # 执行真实打印
        try:
            success = self._barcode_printer.print_barcode(test_barcode, force=True)

            if success:
                self.show_message("成功", f"测试打印: {test_barcode}", "info")
                self.set_status(f"测试打印成功: {test_barcode}")
            else:
                self.show_message("错误", "测试打印失败，请检查打印机状态", "error")
                self.set_status("测试打印失败")

        except Exception as e:
            self.show_message("错误", f"测试打印异常: {e}", "error")

    def set_barcode(self, barcode: str):
        """外部设置条码（用于扫码自动填入）"""
        self.barcode_input.setText(barcode)

    def _manual_unlock(self):
        """手动解锁打印锁定模式（需要admin权限）"""
        main_window = self._get_main_window()

        # 权限检查：需要 admin (2级) 及以上权限
        if main_window and hasattr(main_window, 'auth_manager'):
            auth_manager = main_window.auth_manager
            if not auth_manager.has_permission('admin'):
                # 弹出登录对话框
                from ..dialogs.login_dialog import LoginDialog
                from PySide6.QtWidgets import QDialog
                dialog = LoginDialog(auth_manager, self, required_role='admin')
                if dialog.exec() != QDialog.Accepted:
                    return  # 用户取消登录
                # 登录成功，更新导航栏状态
                if hasattr(main_window, 'sidebar'):
                    main_window.sidebar.update_user_info(auth_manager.get_current_user())

        # 执行解锁
        if main_window and hasattr(main_window, 'scan_controller'):
            main_window.scan_controller.manual_unlock_print()
            self.show_message("提示", "已手动解锁打印锁定状态", "info")
            self._update_lock_status(False, "")
        else:
            self.show_message("错误", "无法获取扫码控制器", "error")

    def _update_lock_status(self, is_locked: bool, locked_code: str):
        """更新锁定状态显示"""
        # 检查功能是否启用
        correction_enabled = self.ui_config.is_print_match_correction_enabled()

        if not correction_enabled:
            # 功能未启用，隐藏所有组件
            self._lock_title_label.hide()
            self.lock_status_label.hide()
            self.manual_unlock_btn.hide()
            return

        # 功能已启用，始终显示状态标签和解锁按钮
        self._lock_title_label.show()
        self.lock_status_label.show()
        self.manual_unlock_btn.show()

        if is_locked and locked_code:
            # 已锁定状态
            self.lock_status_label.setText(locked_code)
            self.lock_status_label.setStyleSheet(f"color: {Colors.WARNING};")
        else:
            # 未锁定状态
            self.lock_status_label.setText("未锁定")
            self.lock_status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")

    def on_print_lock_changed(self, is_locked: bool, locked_code: str):
        """响应打印锁定状态变化（由外部调用）"""
        self._update_lock_status(is_locked, locked_code)

    def refresh(self):
        """刷新页面"""
        self._loading = True
        self._refresh_printers()
        self._load_config()
        # 再次确保打印机选择正确（配置加载后）
        if self._barcode_printer:
            printer_name = self._barcode_printer.get_selected_printer()
            if printer_name:
                index = self.printer_combo.findText(printer_name)
                if index >= 0:
                    self.printer_combo.setCurrentIndex(index)
        self._loading = False

    # ==================== 配方管理方法 ====================

    def _refresh_recipes(self):
        """刷新配方列表到下拉框"""
        self.recipe_combo.blockSignals(True)
        self.recipe_combo.clear()
        recipes = self.ui_config.get_print_recipes()
        for recipe in recipes:
            self.recipe_combo.addItem(recipe['recipe_name'], recipe['id'])
        self.recipe_combo.blockSignals(False)

    def _select_recipe_in_combo(self, recipe_id: int):
        """在下拉框中选中指定配方"""
        for i in range(self.recipe_combo.count()):
            if self.recipe_combo.itemData(i) == recipe_id:
                self.recipe_combo.blockSignals(True)
                self.recipe_combo.setCurrentIndex(i)
                self.recipe_combo.blockSignals(False)
                return
        # 如果找不到，选择第一个
        if self.recipe_combo.count() > 0:
            self.recipe_combo.setCurrentIndex(0)
            self._current_recipe_id = self.recipe_combo.itemData(0)

    def _on_recipe_changed(self, index: int):
        """配方切换时加载对应参数"""
        if self._loading or index < 0:
            return
        recipe_id = self.recipe_combo.itemData(index)
        if recipe_id is None:
            return
        self._current_recipe_id = recipe_id
        self.ui_config.set_current_recipe_id(recipe_id)
        # 加载配方参数
        recipe = self.ui_config.get_print_recipe_by_id(recipe_id)
        if recipe:
            self._loading = True
            self.barcode_type_combo.setCurrentText(recipe.get('barcode_type', 'CODE39'))
            self.label_width_spin.setValue(recipe.get('label_width', 70))
            self.label_height_spin.setValue(recipe.get('label_height', 20))
            self.barcode_width_spin.setValue(recipe.get('barcode_width', 0.25))
            self.barcode_height_spin.setValue(recipe.get('barcode_height', 10))
            self.top_margin_spin.setValue(recipe.get('barcode_top_margin', 2.0))
            self.font_size_spin.setValue(recipe.get('font_size', 12))
            self.text_gap_spin.setValue(recipe.get('text_gap', -1.0))
            self.repeat_count_spin.setValue(recipe.get('auto_print_repeat_count', 1))
            self._loading = False
            self._update_preview()
            self._log(f"[INFO] 已切换到配方: {recipe.get('recipe_name')}")

    def _on_new_recipe(self):
        """新建配方（需要管理员权限）"""
        # 权限检查
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'auth_manager'):
            auth_manager = main_window.auth_manager
            if not auth_manager.has_permission('admin'):
                from ..dialogs.login_dialog import LoginDialog
                from PySide6.QtWidgets import QDialog
                dialog = LoginDialog(auth_manager, self, required_role='admin')
                if dialog.exec() != QDialog.Accepted:
                    return
                if hasattr(main_window, 'sidebar'):
                    main_window.sidebar.update_user_info(auth_manager.get_current_user())
        # 弹出输入框
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "新建配方", "请输入配方名称:")
        if not ok or not name.strip():
            return
        # 使用当前参数创建配方
        params = {
            'barcode_type': self.barcode_type_combo.currentText(),
            'label_width': self.label_width_spin.value(),
            'label_height': self.label_height_spin.value(),
            'barcode_width': self.barcode_width_spin.value(),
            'barcode_height': self.barcode_height_spin.value(),
            'barcode_top_margin': self.top_margin_spin.value(),
            'font_size': self.font_size_spin.value(),
            'text_gap': self.text_gap_spin.value(),
            'auto_print_repeat_count': self.repeat_count_spin.value(),
        }
        new_id = self.ui_config.create_print_recipe(name.strip(), params)
        if new_id:
            self._refresh_recipes()
            self._select_recipe_in_combo(new_id)
            self._current_recipe_id = new_id
            self.ui_config.set_current_recipe_id(new_id)
            self.show_message("成功", f"配方 '{name}' 创建成功", "info")
        else:
            self.show_message("错误", "创建配方失败，名称可能重复", "error")

    def _on_delete_recipe(self):
        """删除配方（需要管理员权限）"""
        if self.recipe_combo.count() <= 1:
            self.show_message("提示", "至少需要保留一个配方", "warning")
            return
        # 权限检查
        main_window = self._get_main_window()
        if main_window and hasattr(main_window, 'auth_manager'):
            auth_manager = main_window.auth_manager
            if not auth_manager.has_permission('admin'):
                from ..dialogs.login_dialog import LoginDialog
                from PySide6.QtWidgets import QDialog
                dialog = LoginDialog(auth_manager, self, required_role='admin')
                if dialog.exec() != QDialog.Accepted:
                    return
                if hasattr(main_window, 'sidebar'):
                    main_window.sidebar.update_user_info(auth_manager.get_current_user())
        # 确认删除
        from PySide6.QtWidgets import QMessageBox
        recipe_name = self.recipe_combo.currentText()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除配方 '{recipe_name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        recipe_id = self.recipe_combo.itemData(self.recipe_combo.currentIndex())
        if self.ui_config.delete_print_recipe(recipe_id):
            self._refresh_recipes()
            if self.recipe_combo.count() > 0:
                self._current_recipe_id = self.recipe_combo.itemData(0)
                self.ui_config.set_current_recipe_id(self._current_recipe_id)
                self._on_recipe_changed(0)
            self.show_message("成功", f"配方 '{recipe_name}' 已删除", "info")
        else:
            self.show_message("错误", "删除配方失败", "error")
