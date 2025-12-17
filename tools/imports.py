# -*- coding: utf-8 -*-
"""
分析运行时加载的所有模块依赖
运行后会生成 imports_report.txt

使用方法:
1. 在 main.py 开头添加: import tools.imports
2. 正常运行程序，使用各项功能
3. 正常退出程序
4. 查看生成的 imports_report.txt
"""

import sys
import atexit

def save_imports():
    """程序退出时保存所有已加载的模块"""
    modules = sorted(sys.modules.keys())

    # 分类整理
    stdlib = []
    pyside6 = []
    third_party = []
    local = []

    # CodeVerifier 项目的第三方库
    THIRD_PARTY_LIBS = (
        # 加密库
        'cryptography', 'cffi', 'pycparser',
        # 串口通信
        'serial', 'pyserial',
        # Windows 打印
        'win32', 'win32print', 'win32ui', 'win32con', 'win32api', 'pywintypes',
        # Excel 处理
        'openpyxl', 'et_xmlfile',
        # 条码生成
        'barcode', 'PIL', 'pillow',
        # 语音播报
        'pygame',
        # 其他可能的依赖
        'sqlite3', 'threading', 'pathlib', 'datetime', 'typing',
        'contextlib', 'traceback', 'functools', 're', 'os', 'sys',
    )

    for mod in modules:
        if mod.startswith('_') or '.' not in mod:
            # 内置模块，跳过细分
            continue

        top_level = mod.split('.')[0]

        if top_level in ('scannerapp', 'core', 'ui'):
            local.append(mod)
        elif top_level == 'PySide6':
            pyside6.append(mod)
        elif top_level in THIRD_PARTY_LIBS:
            third_party.append(mod)

    with open('imports_report.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("CodeVerifier 运行时加载的模块分析报告\n")
        f.write("=" * 60 + "\n\n")

        f.write("【PySide6 模块】({} 个)\n".format(len(pyside6)))
        f.write("-" * 40 + "\n")
        for mod in sorted(set(pyside6)):
            f.write("  {}\n".format(mod))

        f.write("\n【第三方模块】({} 个)\n".format(len(third_party)))
        f.write("-" * 40 + "\n")
        for mod in sorted(set(third_party)):
            f.write("  {}\n".format(mod))

        f.write("\n【本地模块】({} 个)\n".format(len(local)))
        f.write("-" * 40 + "\n")
        for mod in sorted(set(local)):
            f.write("  {}\n".format(mod))

        # 生成 hiddenimports 建议
        f.write("\n" + "=" * 60 + "\n")
        f.write("【建议添加到 spec 文件 hiddenimports 的模块】\n")
        f.write("=" * 60 + "\n")
        f.write("hidden_imports = [\n")

        all_imports = set(pyside6) | set(third_party)
        for mod in sorted(all_imports):
            f.write("    '{}',\n".format(mod))

        f.write("]\n")

    print("\n" + "=" * 50)
    print("依赖分析完成！报告已保存到 imports_report.txt")
    print("=" * 50)

# 注册退出时的回调
atexit.register(save_imports)

print("依赖分析模块已加载，正常退出程序后会生成报告...")
