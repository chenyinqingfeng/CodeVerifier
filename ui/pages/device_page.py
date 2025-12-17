"""
设备连接页面 - 左右两栏卡片式布局
左侧：PLC通信设置 | 右侧：扫码器串口设置
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QGridLayout, QComboBox, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes
from core.serial_handler import SerialHandler


class PLCSettingsCard(QFrame):
    """PLC通信设置卡片"""

    def __init__(self, parent=None, page=None):
        super().__init__(parent)
        self.page = page
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            PLCSettingsCard {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel("🔌 PLC通信设置")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        layout.addWidget(title_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Colors.BORDER};")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # IP地址
        ip_label = QLabel("IP地址")
        ip_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
        layout.addWidget(ip_label)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("例如: 192.168.0.5")
        self.ip_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 12px;
                font-size: 14px;
                font-family: Consolas;
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        layout.addWidget(self.ip_input)

        # 端口号
        port_label = QLabel("端口号")
        port_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
        layout.addWidget(port_label)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("默认: 502")
        self.port_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 12px;
                font-size: 14px;
                font-family: Consolas;
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        layout.addWidget(self.port_input)

        # 连接PLC按钮
        self.connect_btn = QPushButton("🚀 连接PLC")
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """)
        self.connect_btn.clicked.connect(self._connect_plc)
        layout.addWidget(self.connect_btn)

        # 手动发送区域
        send_label = QLabel("手动发送")
        send_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
        layout.addWidget(send_label)

        send_layout = QHBoxLayout()
        send_layout.setSpacing(8)

        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("输入正整数")
        self.manual_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 10px;
                font-size: 14px;
                font-family: Consolas;
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QLineEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        send_layout.addWidget(self.manual_input, 1)

        self.send_btn = QPushButton("📡 发送")
        self.send_btn.setFixedWidth(100)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 10px;
                font-size: 14px;
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #e69500;
            }}
        """)
        self.send_btn.clicked.connect(self._manual_send)
        send_layout.addWidget(self.send_btn)

        layout.addLayout(send_layout)

        # 提示信息
        tip_frame = QFrame()
        tip_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        tip_layout = QVBoxLayout(tip_frame)
        tip_layout.setContentsMargins(12, 8, 12, 8)

        tip_label = QLabel("💡 提示：修改配置后点击【连接PLC】立即生效")
        tip_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 12px;")
        tip_label.setWordWrap(True)
        tip_layout.addWidget(tip_label)

        layout.addWidget(tip_frame)
        layout.addStretch()

    def _load_config(self):
        """加载保存的PLC配置"""
        if not self.page or not hasattr(self.page, 'ui_config'):
            return

        config = self.page.ui_config.get_plc_config()
        self.ip_input.setText(config.get('ip', '192.168.0.5'))
        self.port_input.setText(str(config.get('port', 502)))

    def _get_controller(self):
        if self.page and hasattr(self.page, 'main_window') and hasattr(self.page.main_window, 'scan_controller'):
            return self.page.main_window.scan_controller
        return None

    def _connect_plc(self):
        """连接PLC"""
        ip = self.ip_input.text().strip()
        port = int(self.port_input.text().strip() or "502")

        # 保存PLC配置
        if hasattr(self.page, 'ui_config'):
            self.page.ui_config.set_plc_config(ip, port)

        controller = self._get_controller()
        if controller:
            success = controller.connect_plc(ip, port)
            if success:
                self.page.show_message("成功", f"PLC连接成功: {ip}:{port}", "info")
            else:
                self.page.show_message("失败", f"无法连接到PLC: {ip}:{port}", "error")
        else:
            self.page.show_message("错误", "扫码控制器未初始化", "error")

    def _manual_send(self):
        """手动发送PLC值"""
        value_str = self.manual_input.text().strip()
        if not value_str:
            self.page.show_message("错误", "请输入要发送的数值", "error")
            return

        try:
            value = int(value_str)
            if value < 0:
                self.page.show_message("错误", "请输入非负整数", "error")
                return
        except ValueError:
            self.page.show_message("错误", "请输入有效的整数", "error")
            return

        controller = self._get_controller()
        if controller:
            if value == 1:
                signal = "PASS"
            elif value == 2:
                signal = "FAIL"
            else:
                signal = str(value)

            success = controller.send_to_plc(signal)
            if success:
                self.page.show_message("成功", f"已发送PLC值: {value} ({signal})", "info")
            else:
                self.page.show_message("失败", f"发送PLC值失败: {value}", "error")
        else:
            self.page.show_message("错误", "扫码控制器未初始化", "error")


class ScannerSettingsCard(QFrame):
    """扫码器串口设置卡片"""

    def __init__(self, parent=None, page=None):
        super().__init__(parent)
        self.page = page
        self._setup_ui()
        self._load_serial_ports()
        self._load_config()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            ScannerSettingsCard {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel("📟 扫码器串口设置")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        layout.addWidget(title_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Colors.BORDER};")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 工作模式
        mode_frame = QFrame()
        mode_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: 8px;
            }}
        """)
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(16, 12, 16, 12)

        mode_title = QLabel("⚙️ 工作模式")
        mode_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.TEXT_PRIMARY_LIGHT};")
        mode_layout.addWidget(mode_title)

        self.single_mode_check = QCheckBox("单枪模式（一把扫码枪扫描正反面）")
        self.single_mode_check.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT}; font-size: 13px;")
        self.single_mode_check.stateChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.single_mode_check)

        layout.addWidget(mode_frame)

        # 正面扫码器串口
        front_label = QLabel("正面扫码器串口")
        front_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
        layout.addWidget(front_label)

        self.front_port_combo = QComboBox()
        self.front_port_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 12px;
                font-size: 14px;
                font-family: Consolas;
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QComboBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 40px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid {Colors.PRIMARY};
                margin-right: 15px;
            }}
        """)
        layout.addWidget(self.front_port_combo)

        # 背面扫码器串口
        self.back_label = QLabel("背面扫码器串口")
        self.back_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
        layout.addWidget(self.back_label)

        self.back_port_combo = QComboBox()
        self.back_port_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 12px;
                font-size: 14px;
                font-family: Consolas;
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QComboBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 40px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid {Colors.PRIMARY};
                margin-right: 15px;
            }}
        """)
        layout.addWidget(self.back_port_combo)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.refresh_btn = QPushButton("🔄 刷新串口")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 14px;
                font-size: 14px;
                background-color: {Colors.SURFACE_LIGHT};
                color: {Colors.TEXT_PRIMARY_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BACKGROUND_LIGHT};
            }}
        """)
        self.refresh_btn.clicked.connect(self._load_serial_ports)
        btn_layout.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("🚀 连接扫码枪")
        self.connect_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 14px;
                font-size: 14px;
                font-weight: bold;
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """)
        self.connect_btn.clicked.connect(self._connect_scanners)
        btn_layout.addWidget(self.connect_btn)

        layout.addLayout(btn_layout)

        # 提示信息
        tip_frame = QFrame()
        tip_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: 8px;
            }}
        """)
        tip_layout = QVBoxLayout(tip_frame)
        tip_layout.setContentsMargins(12, 8, 12, 8)

        tip_label = QLabel("💡 提示：点击【刷新串口】扫描可用端口，点击【连接扫码枪】立即生效")
        tip_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 12px;")
        tip_label.setWordWrap(True)
        tip_layout.addWidget(tip_label)

        layout.addWidget(tip_frame)
        layout.addStretch()

    def _get_controller(self):
        if self.page and hasattr(self.page, 'main_window') and hasattr(self.page.main_window, 'scan_controller'):
            return self.page.main_window.scan_controller
        return None

    def _load_serial_ports(self):
        """加载可用串口列表"""
        self.front_port_combo.clear()
        self.back_port_combo.clear()

        ports = SerialHandler.list_ports()

        if ports:
            for port in ports:
                self.front_port_combo.addItem(port['display'], port['device'])
                self.back_port_combo.addItem(port['display'], port['device'])
        else:
            self.front_port_combo.addItem("(未检测到可用串口)", "")
            self.back_port_combo.addItem("(未检测到可用串口)", "")

    def _load_config(self):
        """加载配置"""
        if not self.page or not hasattr(self.page, 'ui_config'):
            return

        config = self.page.ui_config.get_scanner_config()
        front_port = config.get('front_port', 'COM20')
        back_port = config.get('back_port', 'COM21')
        single_mode = config.get('single_mode', False)

        # 设置选中
        for i in range(self.front_port_combo.count()):
            if self.front_port_combo.itemData(i) == front_port:
                self.front_port_combo.setCurrentIndex(i)
                break

        for i in range(self.back_port_combo.count()):
            if self.back_port_combo.itemData(i) == back_port:
                self.back_port_combo.setCurrentIndex(i)
                break

        self.single_mode_check.setChecked(single_mode)
        self._update_back_visibility()

    def _on_mode_changed(self, state):
        """工作模式改变"""
        self._update_back_visibility()

    def _update_back_visibility(self):
        """更新背面串口显示状态"""
        is_single = self.single_mode_check.isChecked()
        self.back_label.setVisible(not is_single)
        self.back_port_combo.setVisible(not is_single)

    def _connect_scanners(self):
        """连接扫码枪"""
        front_port = self.front_port_combo.currentData()
        back_port = self.back_port_combo.currentData()
        single_mode = self.single_mode_check.isChecked()

        if not front_port:
            self.page.show_message("错误", "请先刷新串口列表，选择有效的串口", "error")
            return

        # 保存配置
        if hasattr(self.page, 'ui_config'):
            self.page.ui_config.set_scanner_config(front_port, back_port, single_mode)

        controller = self._get_controller()
        if controller:
            controller.set_single_mode(single_mode)

            # 连接正面扫码枪
            front_success = controller.connect_scanner("front", front_port)

            # 双枪模式连接背面
            back_success = True
            if not single_mode and back_port:
                back_success = controller.connect_scanner("back", back_port)

            if front_success and back_success:
                mode_text = "单枪模式" if single_mode else "双枪模式"
                self.page.show_message("成功", f"扫码枪连接成功\n模式: {mode_text}", "info")
            else:
                self.page.show_message("警告", "部分扫码枪连接失败，请检查串口", "warning")
        else:
            self.page.show_message("错误", "扫码控制器未初始化", "error")


class VoiceSettingsCard(QFrame):
    """语音播报设置卡片"""

    def __init__(self, parent=None, page=None):
        super().__init__(parent)
        self.page = page
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            VoiceSettingsCard {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: 12px;
                border: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel("🔊 语音播报设置")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {Colors.PRIMARY};
        """)
        layout.addWidget(title_label)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {Colors.BORDER};")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 启用开关
        self.enable_check = QCheckBox("启用语音播报")
        self.enable_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY_LIGHT};
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        self.enable_check.stateChanged.connect(self._on_config_changed)
        layout.addWidget(self.enable_check)

        # 音量设置
        volume_label = QLabel("音量调节")
        volume_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
        layout.addWidget(volume_label)

        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(12)

        self.volume_combo = QComboBox()
        self.volume_combo.addItem("50%", 0.5)
        self.volume_combo.addItem("75%", 0.75)
        self.volume_combo.addItem("100% (最大)", 1.0)
        self.volume_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 12px;
                font-size: 14px;
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QComboBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 40px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid {Colors.PRIMARY};
                margin-right: 15px;
            }}
        """)
        self.volume_combo.currentIndexChanged.connect(self._on_config_changed)
        volume_layout.addWidget(self.volume_combo, 1)

        layout.addLayout(volume_layout)

        # 播报次数设置
        repeat_label = QLabel("播报次数")
        repeat_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 13px;")
        layout.addWidget(repeat_label)

        repeat_layout = QHBoxLayout()
        repeat_layout.setSpacing(12)

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem("1次", 1)
        self.repeat_combo.addItem("2次", 2)
        self.repeat_combo.addItem("3次", 3)
        self.repeat_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 12px;
                font-size: 14px;
                background-color: {Colors.BACKGROUND_LIGHT};
                border: 2px solid {Colors.BORDER};
                border-radius: 8px;
            }}
            QComboBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 40px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid {Colors.PRIMARY};
                margin-right: 15px;
            }}
        """)
        self.repeat_combo.currentIndexChanged.connect(self._on_config_changed)
        repeat_layout.addWidget(self.repeat_combo, 1)

        # 测试按钮
        self.test_btn = QPushButton("🎵 测试")
        self.test_btn.setFixedWidth(100)
        self.test_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 12px;
                font-size: 14px;
                background-color: {Colors.WARNING};
                color: white;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #e69500;
            }}
        """)
        self.test_btn.clicked.connect(self._test_voice)
        repeat_layout.addWidget(self.test_btn)

        layout.addLayout(repeat_layout)

        # 提示信息
        tip_frame = QFrame()
        tip_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: 8px;
            }}
        """)
        tip_layout = QVBoxLayout(tip_frame)
        tip_layout.setContentsMargins(12, 8, 12, 8)

        tip_label = QLabel("💡 播报内容：正面匹配、反面匹配、匹配成功、条码无效、重复扫码、二码不一致")
        tip_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT}; font-size: 12px;")
        tip_label.setWordWrap(True)
        tip_layout.addWidget(tip_label)

        layout.addWidget(tip_frame)
        layout.addStretch()

    def _load_config(self):
        """加载语音配置"""
        if not self.page or not hasattr(self.page, 'ui_config'):
            return

        config = self.page.ui_config.get_voice_config()
        self.enable_check.setChecked(config.get('enabled', True))

        volume = config.get('volume', 1.0)
        for i in range(self.volume_combo.count()):
            if self.volume_combo.itemData(i) == volume:
                self.volume_combo.setCurrentIndex(i)
                break
        # 如果没有匹配的，默认选择最大音量
        if self.volume_combo.currentData() != volume:
            self.volume_combo.setCurrentIndex(2)  # 100% (最大)

        repeat = config.get('repeat', 1)
        for i in range(self.repeat_combo.count()):
            if self.repeat_combo.itemData(i) == repeat:
                self.repeat_combo.setCurrentIndex(i)
                break

        self._update_controls_state()

    def _on_config_changed(self, *args):
        """配置改变时自动保存"""
        self._update_controls_state()
        self._auto_save()

    def _update_controls_state(self):
        """更新控件状态"""
        enabled = self.enable_check.isChecked()
        self.volume_combo.setEnabled(enabled)
        self.repeat_combo.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)

    def _auto_save(self):
        """自动保存配置"""
        if not self.page or not hasattr(self.page, 'ui_config'):
            return

        enabled = self.enable_check.isChecked()
        volume = self.volume_combo.currentData()
        repeat = self.repeat_combo.currentData()
        self.page.ui_config.set_voice_config(enabled, 180, volume, repeat)

    def _test_voice(self):
        """测试语音播报"""
        try:
            from core.voice_announcer import get_voice_announcer

            voice = get_voice_announcer(self.page.ui_config if self.page else None)
            voice.announce("匹配成功")
        except ImportError:
            self.page.show_message("错误", "未安装 pygame 库，请先运行: pip install pygame", "error")
        except Exception as e:
            self.page.show_message("错误", f"语音播放失败: {e}", "error")


class DevicePage(BasePage):
    """设备连接页面 - 三栏并排布局"""

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # 三栏并排容器
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        # 左侧：PLC设置
        self.plc_card = PLCSettingsCard(page=self)
        content_layout.addWidget(self.plc_card, 1)

        # 中间：扫码器设置
        self.scanner_card = ScannerSettingsCard(page=self)
        content_layout.addWidget(self.scanner_card, 1)

        # 右侧：语音播报设置
        self.voice_card = VoiceSettingsCard(page=self)
        content_layout.addWidget(self.voice_card, 1)

        layout.addLayout(content_layout)

    def refresh(self):
        """刷新页面"""
        self.plc_card._load_config()
        self.scanner_card._load_serial_ports()
        self.scanner_card._load_config()
        self.voice_card._load_config()
