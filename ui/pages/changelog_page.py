"""
更新日志页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTextEdit, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


# 更新日志数据
CHANGELOGS = [
    {
        "version": "V3.6",
        "date": "2025-12-13",
        "author": "Claude 魏俊辉",
        "changes": [
            "【新增】打印配方管理功能，支持保存多套打印参数组合",
            "【新增】配方一键切换，快速切换不同标签规格",
            "【新增】自动重复打印次数设置（1-10次）",
            "【新增】配方新建/删除功能（需管理员权限）",
            "【新增】修改参数自动保存到当前配方",
            "【新增】启动程序自动加载上次使用的配方",
            "【优化】打印设置页面添加滚动条，适配更多参数",
            "【优化】启用开关和锁定验证合并为一行，布局更紧凑",
            "【优化】批次详情表格设置为只读，禁止编辑",
            "【优化】批次详情扫码时间、打印时间列宽扩宽，完整显示",
        ]
    },
    {
        "version": "V3.5",
        "date": "2025-12-12",
        "author": "Claude 魏俊辉",
        "changes": [
            "【新增】打印后锁定验证功能，防止漏扫、错扫、不匹配",
            "【新增】打印成功后自动锁定，两把枪都扫到相同条码才能解锁",
            "【新增】锁定状态下扫错码报警（PLC FAIL + 语音提示）",
            "【新增】锁定状态下扫对码解除报警（PLC PASS）",
            "【新增】手动解锁按钮，需要管理员权限",
            "【新增】TopBar和打印页面显示锁定状态",
            "【新增】语音播报「解锁条码错误」提示音",
            "【优化】锁定验证功能默认启用，可在打印设置中关闭",
        ]
    },
    {
        "version": "V3.4",
        "date": "2025-12-08",
        "author": "Claude 魏俊辉",
        "changes": [
            "【新增】语音播报功能，扫码结果自动语音提示",
            "【新增】语音播报设置：启用/禁用、音量调节、播报次数",
            "【新增】语音播报内容：正面匹配、反面匹配、匹配成功、条码无效、重复扫码、二码不一致",
            "【优化】采用 Edge-TTS 晓晓女声预录音频，音质更清晰",
            "【优化】音频后期增强 +12dB，音量更大更响亮",
            "【优化】设备连接页面三栏并排布局（PLC、扫码器、语音播报）",
            "【优化】语音设置自动保存，无需手动点击保存按钮",
        ]
    },
    {
        "version": "V3.3",
        "date": "2025-12-01",
        "author": "Claude 魏俊辉",
        "changes": [
            "【新增】更新日志页面，可查看历史版本更新内容",
            "【优化】侧边栏折叠功能，折叠按钮更大更清晰",
            "【优化】侧边栏折叠时退出按钮显示为「退出」适配宽度",
            "【优化】启动时默认最大化窗口",
            "【优化】批次创建时严格校验编号格式，保留前导零",
            "【优化】批次编辑只允许修改客户和货柜号，保护条码数据",
            "【优化】批次列表进度显示为百分比，100%显示绿色",
            "【优化】打印参数输入框不响应鼠标滚轮，防止误操作",
            "【修复】批次名称格式改为完整首尾条码显示",
            "【修复】批次列表列宽和对齐问题",
            "【修复】批次编辑后扫码验证表格不刷新，现在编辑客户/货柜号后自动刷新显示",
            "【修复】扫码后条码未同步到打印页面，现在任意枪扫码后自动填入当前条码供手动补打",
            "【修复】扫码日志导出Excel格式错误，适配新的日志结构（扫码枪、扫码数据、结果说明）",
        ]
    },
    {
        "version": "V3.2",
        "date": "2025-11-15",
        "author": "Claude 魏俊辉",
        "changes": [
            "【新增】PySide6 Qt版本全新重构",
            "【新增】现代化UI界面设计",
            "【新增】侧边栏导航，支持折叠",
            "【新增】用户权限管理系统",
            "【新增】批次管理功能",
            "【新增】条码打印功能",
            "【新增】数据导出功能",
            "【新增】日志查看功能",
            "【新增】设备连接管理",
            "【新增】客户管理功能",
            "【优化】扫码验证流程",
            "【优化】数据库结构",
        ]
    },
    {
        "version": "V3.1",
        "date": "2025-10-01",
        "author": "Claude 魏俊辉",
        "changes": [
            "【新增】CustomTkinter版本",
            "【新增】基础扫码验证功能",
            "【新增】批次管理基础功能",
            "【新增】SQLite数据库支持",
        ]
    },
]


class ChangelogPage(BasePage):
    """更新日志页面"""

    def __init__(self, db_manager, ui_config, parent=None):
        super().__init__(db_manager, ui_config, parent)

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题栏
        header = QHBoxLayout()

        title = QLabel("更新日志")
        title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_2XL, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        header.addWidget(title)

        header.addStretch()

        # 版本选择下拉框
        version_label = QLabel("选择版本：")
        version_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        header.addWidget(version_label)

        self.version_combo = QComboBox()
        self.version_combo.setFixedWidth(120)
        self.version_combo.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        for log in CHANGELOGS:
            self.version_combo.addItem(log["version"], log)
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        header.addWidget(self.version_combo)

        layout.addLayout(header)

        # 内容区域
        content_frame = QFrame()
        content_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 1px solid {Colors.BORDER};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        # 版本信息头
        self.info_layout = QHBoxLayout()

        self.version_label = QLabel()
        self.version_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XL, QFont.Bold))
        self.version_label.setStyleSheet(f"color: {Colors.PRIMARY};")
        self.info_layout.addWidget(self.version_label)

        self.info_layout.addSpacing(24)

        self.date_label = QLabel()
        self.date_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.date_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        self.info_layout.addWidget(self.date_label)

        self.info_layout.addSpacing(24)

        self.author_label = QLabel()
        self.author_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        self.author_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        self.info_layout.addWidget(self.author_label)

        self.info_layout.addStretch()
        content_layout.addLayout(self.info_layout)

        # 分割线
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {Colors.BORDER};")
        content_layout.addWidget(separator)

        # 更新内容
        self.changes_text = QTextEdit()
        self.changes_text.setReadOnly(True)
        self.changes_text.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE))
        self.changes_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {Colors.TEXT_PRIMARY_LIGHT};
                line-height: 1.8;
            }}
        """)
        content_layout.addWidget(self.changes_text)

        layout.addWidget(content_frame)

        # 默认显示最新版本
        self._show_changelog(CHANGELOGS[0])

    def _on_version_changed(self, index):
        """版本选择改变"""
        log = self.version_combo.currentData()
        if log:
            self._show_changelog(log)

    def _show_changelog(self, log: dict):
        """显示更新日志"""
        self.version_label.setText(log["version"])
        self.date_label.setText(f"📅 {log['date']}")
        self.author_label.setText(f"👤 {log['author']}")

        # 格式化更新内容
        changes_html = "<ul style='margin: 0; padding-left: 20px; line-height: 2;'>"
        for change in log["changes"]:
            # 根据类型设置颜色
            if change.startswith("【新增】"):
                color = Colors.SUCCESS
            elif change.startswith("【优化】"):
                color = Colors.PRIMARY
            elif change.startswith("【修复】"):
                color = Colors.WARNING
            else:
                color = Colors.TEXT_PRIMARY_LIGHT

            changes_html += f"<li style='color: {color}; margin: 8px 0;'>{change}</li>"
        changes_html += "</ul>"

        self.changes_text.setHtml(changes_html)

    def refresh(self):
        """刷新页面"""
        pass
