# CodeVerifier 条码验证系统

<p align="center">
  <img src="app.ico" width="128" height="128" alt="CodeVerifier">
</p>

<p align="center">
  <strong>工业级二码合一扫码验证系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/PySide6-6.5+-green.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/License-Private-red.svg" alt="License">
</p>

---

## 📋 项目简介

CodeVerifier 是一款面向生产制造业的条码验证系统，实现产品正反面条码的"二码合一"自动匹配验证，确保产品追溯准确性和生产质量管控。

## ✨ 核心功能

| 模块 | 功能描述 |
|------|---------|
| 🔍 **扫码验证** | 双扫码枪同步采集，正反面条码自动匹配验证 |
| 📦 **批次管理** | 批次创建、导入导出、进度追踪、归档管理 |
| 🖨️ **条码打印** | 自动打印条码标签，支持多种条码格式 |
| 🔊 **语音播报** | 实时语音反馈扫码结果，提升操作效率 |
| 🔌 **PLC 通信** | Modbus 协议对接 PLC，自动发送 PASS/FAIL 信号 |
| 📊 **数据导出** | 支持 Excel 批量导出，多维度数据查询 |
| 👥 **用户权限** | 多级用户权限管理，操作日志完整记录 |

## 🛠️ 技术架构

```
CodeVerifier/
├── main.py                 # 程序入口
├── core/                   # 核心业务逻辑
│   ├── scan_controller.py  # 扫码控制器
│   ├── database_manager.py # 数据库管理（SQLite）
│   ├── serial_handler.py   # 串口通信
│   ├── plc_handler.py      # PLC Modbus 通信
│   ├── barcode_printer.py  # 条码打印
│   └── voice_announcer.py  # 语音播报（pygame）
├── ui/                     # 用户界面（PySide6）
│   ├── main_window.py      # 主窗口
│   ├── pages/              # 功能页面
│   ├── dialogs/            # 对话框
│   └── components/         # 可复用组件
└── resources/              # 资源文件
    └── audio/              # 语音音频
```

## 🔧 技术栈

- **GUI 框架**: PySide6 (Qt for Python)
- **数据库**: SQLite + 双库架构（生产库/系统库）
- **串口通信**: PySerial
- **工业协议**: Modbus TCP/RTU
- **条码生成**: python-barcode + Pillow
- **音频播放**: pygame
- **Excel 处理**: openpyxl
- **代码保护**: Cython 编译为 .pyd

## 📦 打包部署

```bash
# Cython 编译 + PyInstaller 打包
Build.bat
```

构建产物：`条码验证系统.exe`（单文件，约 70MB）

## 🖼️ 功能截图

> *截图待补充*

## 📄 License

本项目采用 [MIT License](LICENSE) 开源。

允许自由使用、复制、修改、合并、发布、分发和商用，但须保留原始版权声明和许可证文本。

<p align="center">
  <sub>Built with ❤️ by Wei Junhui</sub>
</p>
