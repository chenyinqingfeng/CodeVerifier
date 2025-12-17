# -*- mode: python ; coding: utf-8 -*-
"""
扫码验证系统 Qt版本 - PyInstaller 打包配置
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 项目数据文件（SQL脚本、音频文件等）
app_datas = [
    ('core/*.sql', 'core'),
    ('resources/audio/*.wav', 'resources/audio'),
]

# 隐藏导入（运行时动态加载的模块）
hidden_imports = [
    # PySide6 核心
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.support',
    'PySide6.support.deprecated',
    'PySide6.support.feature',
    'PySide6.support.signature',
    'PySide6.support.signature.errorhandler',
    'PySide6.support.signature.importhandler',
    'PySide6.support.signature.layout',
    'PySide6.support.signature.lib',
    'PySide6.support.signature.lib.enum_sig',
    'PySide6.support.signature.lib.pyi_generator',
    'PySide6.support.signature.lib.tool',
    'PySide6.support.signature.mapping',
    'PySide6.support.signature.parser',

    # PIL/Pillow 图像处理
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageWin',
    'PIL._imaging',
    'PIL._imagingft',

    # barcode 条码生成
    'barcode',
    'barcode.base',
    'barcode.codex',
    'barcode.ean',
    'barcode.upc',
    'barcode.isxn',
    'barcode.itf',
    'barcode.codabar',
    'barcode.writer',
    'barcode.charsets',
    'barcode.charsets.code39',
    'barcode.charsets.code128',

    # cryptography 加密
    'cryptography',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.ciphers',
    'cryptography.hazmat.primitives.ciphers.algorithms',
    'cryptography.hazmat.primitives.ciphers.modes',
    'cryptography.hazmat.primitives.hashes',
    'cryptography.hazmat.primitives.asymmetric',
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.primitives.asymmetric.padding',
    'cryptography.hazmat.primitives.serialization',
    'cryptography.hazmat.bindings._rust',

    # openpyxl Excel处理
    'openpyxl',
    'openpyxl.cell',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.reader',
    'openpyxl.writer',
    'openpyxl.xml',
    'et_xmlfile',

    # pygame 音频播放
    'pygame',
    'pygame.base',
    'pygame.mixer',
    'pygame.mixer_music',
    'pygame.time',
    'pygame.constants',

    # serial 串口通信
    'serial',
    'serial.serialutil',
    'serial.serialwin32',
    'serial.tools',
    'serial.tools.list_ports',
    'serial.tools.list_ports_windows',
    'serial.win32',

    # win32 Windows API
    'win32',
    'win32.lib',
    'win32.lib.win32con',
    'win32print',
    'win32ui',
    'win32api',
    'pywintypes',

    # 标准库（可能被动态加载）
    'sqlite3',
    'sqlite3.dbapi2',
]

# 排除不需要的大模块
excludes = [
    # 不需要的 Python 模块
    'tkinter',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'IPython',
    'jupyter',
    'pytest',
    'unittest',
    # 不需要的 PySide6 模块（这些很大）
    'PySide6.Qt3DAnimation',
    'PySide6.Qt3DCore',
    'PySide6.Qt3DExtras',
    'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic',
    'PySide6.Qt3DRender',
    'PySide6.QtBluetooth',
    'PySide6.QtCharts',
    'PySide6.QtConcurrent',
    'PySide6.QtDataVisualization',
    'PySide6.QtDesigner',
    'PySide6.QtHelp',
    'PySide6.QtLocation',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtNetworkAuth',
    'PySide6.QtNfc',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
    'PySide6.QtPdf',
    'PySide6.QtPdfWidgets',
    'PySide6.QtPositioning',
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'PySide6.QtQuick3D',
    'PySide6.QtQuickControls2',
    'PySide6.QtQuickWidgets',
    'PySide6.QtRemoteObjects',
    'PySide6.QtScxml',
    'PySide6.QtSensors',
    'PySide6.QtSerialBus',
    'PySide6.QtSerialPort',
    'PySide6.QtSpatialAudio',
    'PySide6.QtSql',
    'PySide6.QtStateMachine',
    'PySide6.QtSvg',
    'PySide6.QtSvgWidgets',
    'PySide6.QtTest',
    'PySide6.QtTextToSpeech',
    'PySide6.QtUiTools',
    'PySide6.QtWebChannel',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineQuick',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebSockets',
    'PySide6.QtXml',
    'PySide6.scripts',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=app_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='条码验证系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用 UPX 压缩
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
)
