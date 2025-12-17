"""
备份恢复确认对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..styles import Colors, Fonts, Sizes


class BackupRestoreDialog(QDialog):
    """备份恢复确认对话框"""

    def __init__(self, backup_info: dict, backup_stats: dict = None, parent=None):
        super().__init__(parent)
        self.backup_info = backup_info
        self.backup_stats = backup_stats or {}
        self.restore_production = True
        self.restore_system = True

        self.setWindowTitle("恢复数据库备份")
        self.setFixedSize(550, 600)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border: none;
            }}
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(24, 24, 24, 24)
        scroll_layout.setSpacing(16)

        # 警告横幅
        self._create_warning_banner(scroll_layout)

        # 备份文件信息
        self._create_backup_info_section(scroll_layout)

        # 严重后果警告
        self._create_consequences_section(scroll_layout)

        # 数据预览
        if self.backup_stats:
            self._create_data_preview_section(scroll_layout)

        # 数据库选择
        self._create_selection_section(scroll_layout)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        # 底部按钮区域（固定）
        self._create_button_section(layout)

    def _create_warning_banner(self, parent_layout):
        """创建警告横幅"""
        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background-color: #fee2e2;
                border-radius: {Sizes.RADIUS_MD}px;
                border: 2px solid #fca5a5;
            }}
        """)

        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(20, 16, 20, 16)
        banner_layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("⚠️")
        icon.setFont(QFont(Fonts.FAMILY, 36))
        icon.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(icon)

        title = QLabel("警告：此操作不可撤销")
        title.setFont(QFont(Fonts.FAMILY, 16, QFont.Bold))
        title.setStyleSheet("color: #dc2626;")
        title.setAlignment(Qt.AlignCenter)
        banner_layout.addWidget(title)

        parent_layout.addWidget(banner)

    def _create_backup_info_section(self, parent_layout):
        """创建备份信息区域"""
        section = self._create_section("📁 备份文件信息")

        info_layout = QGridLayout()
        info_layout.setSpacing(8)

        # 备份时间
        info_layout.addWidget(QLabel("备份时间:"), 0, 0)
        time_label = QLabel(self.backup_info.get('time', '未知'))
        time_label.setFont(QFont(Fonts.FAMILY, 11, QFont.Bold))
        time_label.setStyleSheet(f"color: {Colors.PRIMARY};")
        info_layout.addWidget(time_label, 0, 1)

        # 文件名
        info_layout.addWidget(QLabel("文件名:"), 1, 0)
        name_label = QLabel(self.backup_info.get('filename', '未知'))
        name_label.setFont(QFont(Fonts.FAMILY, 11, QFont.Bold))
        info_layout.addWidget(name_label, 1, 1)

        # 文件大小
        info_layout.addWidget(QLabel("文件大小:"), 2, 0)
        size_label = QLabel(self.backup_info.get('size', '未知'))
        size_label.setFont(QFont(Fonts.FAMILY, 11, QFont.Bold))
        info_layout.addWidget(size_label, 2, 1)

        section.layout().addLayout(info_layout)
        parent_layout.addWidget(section)

    def _create_consequences_section(self, parent_layout):
        """创建后果警告区域"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background-color: #fef3c7;
                border-radius: {Sizes.RADIUS_MD}px;
                border: 1px solid #fcd34d;
            }}
        """)

        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(16, 12, 16, 12)
        section_layout.setSpacing(8)

        title = QLabel("⚡ 恢复此备份将导致：")
        title.setFont(QFont(Fonts.FAMILY, 12, QFont.Bold))
        title.setStyleSheet("color: #92400e;")
        section_layout.addWidget(title)

        warnings = [
            "1. 当前数据库将被完全替换",
            "2. 所有未备份的数据将永久丢失",
            "3. 用户、批次、扫描记录等所有数据都将回滚到备份时刻",
            "4. 此操作无法撤销，无法恢复丢失的数据"
        ]

        for warning in warnings:
            label = QLabel(warning)
            label.setStyleSheet("color: #78350f; font-size: 11px;")
            section_layout.addWidget(label)

        parent_layout.addWidget(section)

    def _create_data_preview_section(self, parent_layout):
        """创建数据预览区域"""
        section = self._create_section("📊 备份数据预览")

        grid = QGridLayout()
        grid.setSpacing(12)

        stats = [
            ("批次总数", self.backup_stats.get('batch_count', 0)),
            ("条码总数", self.backup_stats.get('barcode_count', 0)),
            ("扫描记录", self.backup_stats.get('scan_log_count', 0)),
            ("用户总数", self.backup_stats.get('user_count', 0)),
            ("客户总数", self.backup_stats.get('customer_count', 0)),
        ]

        for i, (label, value) in enumerate(stats):
            row, col = i // 2, i % 2

            stat_frame = QFrame()
            stat_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.BACKGROUND_LIGHT};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """)
            stat_layout = QHBoxLayout(stat_frame)
            stat_layout.setContentsMargins(10, 6, 10, 6)

            name = QLabel(label)
            name.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
            stat_layout.addWidget(name)

            stat_layout.addStretch()

            val = QLabel(str(value))
            val.setFont(QFont(Fonts.FAMILY, 11, QFont.Bold))
            val.setStyleSheet(f"color: {Colors.PRIMARY};")
            stat_layout.addWidget(val)

            grid.addWidget(stat_frame, row, col)

        section.layout().addLayout(grid)
        parent_layout.addWidget(section)

    def _create_selection_section(self, parent_layout):
        """创建数据库选择区域"""
        section = self._create_section("🔧 选择要恢复的数据库")

        # 生产数据库
        self.prod_checkbox = QCheckBox("生产数据库 (批次、条码、扫描记录、客户)")
        self.prod_checkbox.setChecked(True)
        self.prod_checkbox.setFont(QFont(Fonts.FAMILY, 11))
        section.layout().addWidget(self.prod_checkbox)

        # 系统数据库
        self.sys_checkbox = QCheckBox("系统数据库 (用户、权限、操作日志)")
        self.sys_checkbox.setChecked(True)
        self.sys_checkbox.setFont(QFont(Fonts.FAMILY, 11))
        section.layout().addWidget(self.sys_checkbox)

        # 提示
        hint = QLabel("💡 提示：默认恢复两个数据库，您可以取消勾选不需要恢复的数据库")
        hint.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT}; font-size: 10px;")
        hint.setWordWrap(True)
        section.layout().addWidget(hint)

        parent_layout.addWidget(section)

    def _create_button_section(self, parent_layout):
        """创建底部按钮区域"""
        bottom = QFrame()
        bottom.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-top: 1px solid {Colors.BORDER};
            }}
        """)

        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(24, 16, 24, 16)
        bottom_layout.setSpacing(12)

        # 最终确认提示
        confirm_frame = QFrame()
        confirm_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #fecaca;
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)
        confirm_layout = QHBoxLayout(confirm_frame)
        confirm_layout.setContentsMargins(16, 10, 16, 10)

        confirm_label = QLabel("请仔细确认以上信息，确定要恢复此备份吗？")
        confirm_label.setFont(QFont(Fonts.FAMILY, 11, QFont.Bold))
        confirm_label.setStyleSheet("color: #991b1b;")
        confirm_label.setAlignment(Qt.AlignCenter)
        confirm_layout.addWidget(confirm_label)

        bottom_layout.addWidget(confirm_frame)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumHeight(42)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Sizes.RADIUS_MD}px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.BACKGROUND_LIGHT};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认恢复")
        confirm_btn.setMinimumHeight(42)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #dc2626;
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #b91c1c;
            }}
        """)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)

        bottom_layout.addLayout(btn_layout)
        parent_layout.addWidget(bottom)

    def _create_section(self, title: str) -> QFrame:
        """创建区块"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setFont(QFont(Fonts.FAMILY, 12, QFont.Bold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        layout.addWidget(title_label)

        return section

    def _on_confirm(self):
        """确认恢复"""
        if not self.prod_checkbox.isChecked() and not self.sys_checkbox.isChecked():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "请至少选择一个数据库进行恢复！")
            return

        self.restore_production = self.prod_checkbox.isChecked()
        self.restore_system = self.sys_checkbox.isChecked()
        self.accept()

    def get_selections(self) -> tuple:
        """获取选择结果"""
        return self.restore_production, self.restore_system
