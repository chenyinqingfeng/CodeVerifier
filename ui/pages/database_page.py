"""
数据库管理页面 - 重新设计
"""

from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from pathlib import Path
from datetime import datetime
import zipfile
import shutil
import tempfile
import os

from .base_page import BasePage
from ..styles import Colors, Fonts, Sizes


class DatabasePage(BasePage):
    """数据库管理页面"""

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 左侧栏 (固定宽度)
        left_column = QWidget()
        left_column.setFixedWidth(360)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Production Database 卡片 (拉伸)
        prod_card = self._setup_production_card(left_layout)
        left_layout.setStretchFactor(prod_card, 1)

        # System Database 卡片 (拉伸)
        sys_card = self._setup_system_card(left_layout)
        left_layout.setStretchFactor(sys_card, 1)

        # 备份状态卡片 (拉伸)
        backup_card = self._setup_backup_status_card(left_layout)
        left_layout.setStretchFactor(backup_card, 1)

        layout.addWidget(left_column)

        # 右侧栏
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 备份列表
        self._setup_backup_list(right_layout)

        # 数据清理（危险操作）
        self._setup_data_cleanup(right_layout)

        layout.addWidget(right_column, 1)

    def _create_card(self, title: str, icon: str, border_color: str, header_color: str = None) -> tuple:
        """创建卡片容器"""
        card = QFrame()
        card.setObjectName("dbCard")
        card.setStyleSheet(f"""
            QFrame#dbCard {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
                border: 2px solid {border_color};
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(2, 2, 2, 2)
        card_layout.setSpacing(0)

        # 卡片头部
        header = QFrame()
        header.setObjectName("cardHeader")
        bg_color = header_color or border_color
        header.setStyleSheet(f"""
            QFrame#cardHeader {{
                background-color: {bg_color};
                border-radius: {Sizes.RADIUS_MD}px;
            }}
        """)
        header.setFixedHeight(36)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 0, 14, 0)

        title_label = QLabel(f"{icon}  {title}")
        title_label.setFont(QFont(Fonts.FAMILY, 12, QFont.Bold))
        title_label.setStyleSheet("color: white; background: transparent;")
        header_layout.addWidget(title_label)

        card_layout.addWidget(header)

        # 卡片内容区
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 10, 14, 14)
        content_layout.setSpacing(6)

        card_layout.addWidget(content)

        return card, content_layout

    def _add_stat_row(self, layout, label: str, value: str, color: str = None):
        """添加统计行"""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(0)

        label_widget = QLabel(label)
        label_widget.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
        label_widget.setStyleSheet(f"color: {Colors.TEXT_SECONDARY_LIGHT};")
        row_layout.addWidget(label_widget)

        row_layout.addStretch()

        value_widget = QLabel(value)
        value_widget.setFont(QFont(Fonts.FAMILY, 11, QFont.Bold))
        value_color = color or Colors.TEXT_PRIMARY_LIGHT
        value_widget.setStyleSheet(f"color: {value_color};")
        row_layout.addWidget(value_widget)

        layout.addWidget(row)
        return value_widget

    def _setup_production_card(self, parent_layout):
        """设置生产数据库卡片"""
        card, content_layout = self._create_card("Production Database", "📊", Colors.PRIMARY)

        self.prod_size_label = self._add_stat_row(content_layout, "文件大小", "-", Colors.SUCCESS)
        self.prod_batch_label = self._add_stat_row(content_layout, "批次总数", "-", Colors.PRIMARY)
        self.prod_barcode_label = self._add_stat_row(content_layout, "条码总数", "-", Colors.SUCCESS)
        self.prod_scan_label = self._add_stat_row(content_layout, "扫描记录", "-", Colors.TEXT_SECONDARY_LIGHT)
        self.prod_customer_label = self._add_stat_row(content_layout, "客户数量", "-", Colors.TEXT_SECONDARY_LIGHT)

        content_layout.addStretch()  # 内容底部弹性空间

        parent_layout.addWidget(card)
        return card

    def _setup_system_card(self, parent_layout):
        """设置系统数据库卡片"""
        card, content_layout = self._create_card("System Database", "⚙️", Colors.WARNING)

        self.sys_size_label = self._add_stat_row(content_layout, "文件大小", "-", Colors.SUCCESS)
        self.sys_user_label = self._add_stat_row(content_layout, "用户数量", "-", Colors.PRIMARY)
        self.sys_log_label = self._add_stat_row(content_layout, "系统日志", "-", Colors.TEXT_SECONDARY_LIGHT)
        self.sys_config_label = self._add_stat_row(content_layout, "配置项数", "-", Colors.TEXT_SECONDARY_LIGHT)

        content_layout.addStretch()  # 内容底部弹性空间

        parent_layout.addWidget(card)
        return card

    def _setup_backup_status_card(self, parent_layout):
        """设置备份状态卡片"""
        card, content_layout = self._create_card("备份状态", "📦", Colors.SUCCESS)

        self.last_backup_label = self._add_stat_row(content_layout, "最后备份", "从未", Colors.TEXT_MUTED_LIGHT)
        self.backup_count_label = self._add_stat_row(content_layout, "备份数量", "0 个", Colors.TEXT_SECONDARY_LIGHT)
        self.backup_size_label = self._add_stat_row(content_layout, "总大小", "0.00 MB", Colors.TEXT_SECONDARY_LIGHT)

        content_layout.addSpacing(6)

        # 操作按钮 - 立即备份用主色调
        backup_btn = QPushButton("立即备份")
        backup_btn.setMinimumHeight(36)
        backup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        backup_btn.clicked.connect(self._backup_database)
        content_layout.addWidget(backup_btn)

        open_folder_btn = QPushButton("打开备份文件夹")
        open_folder_btn.setMinimumHeight(32)
        open_folder_btn.setProperty("secondary", True)
        open_folder_btn.clicked.connect(self._open_backup_folder)
        content_layout.addWidget(open_folder_btn)

        content_layout.addStretch()  # 内容底部弹性空间

        parent_layout.addWidget(card)
        return card

    def _setup_backup_list(self, parent_layout):
        """设置备份列表"""
        # 标题栏
        title_frame = QWidget()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("📋 备份列表")
        title.setFont(QFont(Fonts.FAMILY, 14, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        title_layout.addWidget(title)

        title_layout.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setProperty("secondary", True)
        refresh_btn.setFixedHeight(28)
        refresh_btn.clicked.connect(self.refresh)
        title_layout.addWidget(refresh_btn)

        parent_layout.addWidget(title_frame)

        # 列表容器
        list_frame = QFrame()
        list_frame.setObjectName("backupListFrame")
        list_frame.setStyleSheet(f"""
            QFrame#backupListFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
            }}
        """)

        list_outer_layout = QVBoxLayout(list_frame)
        list_outer_layout.setContentsMargins(0, 0, 0, 0)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        self.backup_list_widget = QWidget()
        self.backup_list_layout = QVBoxLayout(self.backup_list_widget)
        self.backup_list_layout.setContentsMargins(12, 12, 12, 12)
        self.backup_list_layout.setSpacing(8)
        self.backup_list_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(self.backup_list_widget)
        list_outer_layout.addWidget(scroll_area)

        parent_layout.addWidget(list_frame, 3)  # 备份列表占3份空间

    def _setup_data_cleanup(self, parent_layout):
        """设置数据清理区域"""
        cleanup_frame = QFrame()
        cleanup_frame.setObjectName("cleanupFrame")
        cleanup_frame.setStyleSheet(f"""
            QFrame#cleanupFrame {{
                background-color: {Colors.SURFACE_LIGHT};
                border-radius: {Sizes.RADIUS_LG}px;
                border: 2px solid {Colors.ERROR};
            }}
        """)
        cleanup_frame.setMinimumHeight(180)  # 设置最小高度

        cleanup_layout = QVBoxLayout(cleanup_frame)
        cleanup_layout.setContentsMargins(20, 16, 20, 16)
        cleanup_layout.setSpacing(12)

        # 标题
        title = QLabel("⚠️ 数据清理")
        title.setFont(QFont(Fonts.FAMILY, 14, QFont.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        cleanup_layout.addWidget(title)

        # 警告
        warning = QLabel("警告: 以下操作不可恢复，请谨慎操作！")
        warning.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px; font-weight: bold;")
        cleanup_layout.addWidget(warning)

        cleanup_layout.addSpacing(8)

        # 按钮 - 垂直布局更清晰
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        danger_btn_style = f"""
            QPushButton {{
                background-color: {Colors.ERROR};
                color: white;
                border: none;
                border-radius: {Sizes.RADIUS_MD}px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
        """

        clear_sys_btn = QPushButton("清理系统日志")
        clear_sys_btn.setStyleSheet(danger_btn_style)
        clear_sys_btn.clicked.connect(self._clear_system_logs)
        btn_layout.addWidget(clear_sys_btn)

        clear_scan_btn = QPushButton("清理扫描日志")
        clear_scan_btn.setStyleSheet(danger_btn_style)
        clear_scan_btn.clicked.connect(self._clear_scan_logs)
        btn_layout.addWidget(clear_scan_btn)

        clear_archived_btn = QPushButton("清理归档批次")
        clear_archived_btn.setStyleSheet(danger_btn_style)
        clear_archived_btn.clicked.connect(self._clear_archived_batches)
        btn_layout.addWidget(clear_archived_btn)

        # 批次管理按钮
        batch_manage_btn = QPushButton("批次管理")
        batch_manage_btn.setStyleSheet(danger_btn_style)
        batch_manage_btn.clicked.connect(self._show_batch_manage_dialog)
        btn_layout.addWidget(batch_manage_btn)

        btn_layout.addStretch()
        cleanup_layout.addLayout(btn_layout)

        cleanup_layout.addStretch()

        parent_layout.addWidget(cleanup_frame, 1)  # 给予拉伸权重

    def _add_backup_item(self, backup_info: dict):
        """添加备份项到列表"""
        item = QFrame()
        item.setObjectName("backupItem")
        item.setStyleSheet(f"""
            QFrame#backupItem {{
                background-color: {Colors.BACKGROUND_LIGHT};
                border-radius: {Sizes.RADIUS_MD}px;
                border: 1px solid {Colors.BORDER};
            }}
            QFrame#backupItem:hover {{
                border-color: {Colors.PRIMARY};
            }}
        """)

        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(12, 8, 12, 8)
        item_layout.setSpacing(12)
        item_layout.setAlignment(Qt.AlignVCenter)

        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        filename = QLabel(backup_info['filename'])
        filename.setFont(QFont(Fonts.FAMILY, 11, QFont.Bold))
        filename.setStyleSheet(f"color: {Colors.TEXT_PRIMARY_LIGHT};")
        info_layout.addWidget(filename)

        details = QLabel(f"{backup_info['time']}  |  {backup_info['size']}")
        details.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XS))
        details.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT};")
        info_layout.addWidget(details)

        item_layout.addLayout(info_layout)
        item_layout.addStretch()

        # 按钮区域
        restore_btn = QPushButton("恢复")
        restore_btn.setFixedSize(60, 30)
        restore_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SUCCESS};
                color: white;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #27ae60; }}
        """)
        # 使用 partial 替代 lambda，避免 Cython 编译后闭包问题
        restore_btn.clicked.connect(partial(self._on_restore_clicked, backup_info))
        item_layout.addWidget(restore_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setFixedSize(60, 30)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ERROR};
                color: white;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #c0392b; }}
        """)
        delete_btn.clicked.connect(partial(self._on_delete_clicked, backup_info['path']))
        item_layout.addWidget(delete_btn)

        self.backup_list_layout.addWidget(item)

    def _refresh_db_info(self):
        """刷新数据库信息"""
        try:
            # Production database
            prod_path = Path("data/production.db")
            if prod_path.exists():
                size_mb = prod_path.stat().st_size / (1024 * 1024)
                self.prod_size_label.setText(f"{size_mb:.2f} MB")

                try:
                    with self.db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM batches")
                        self.prod_batch_label.setText(str(cursor.fetchone()[0]))

                        cursor.execute("SELECT COUNT(*) FROM barcodes")
                        count = cursor.fetchone()[0]
                        self.prod_barcode_label.setText(f"{count:,}")

                        cursor.execute("SELECT COUNT(*) FROM scan_logs")
                        self.prod_scan_label.setText(str(cursor.fetchone()[0]))

                        cursor.execute("SELECT COUNT(*) FROM customers")
                        self.prod_customer_label.setText(str(cursor.fetchone()[0]))
                except Exception as e:
                    print(f"获取production统计失败: {e}")
            else:
                self.prod_size_label.setText("不存在")

            # System database
            sys_path = Path("data/system.db")
            if sys_path.exists():
                size_mb = sys_path.stat().st_size / (1024 * 1024)
                self.sys_size_label.setText(f"{size_mb:.2f} MB")

                try:
                    with self.db_manager.get_connection('system') as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM users")
                        self.sys_user_label.setText(str(cursor.fetchone()[0]))

                        cursor.execute("SELECT COUNT(*) FROM system_logs")
                        self.sys_log_label.setText(str(cursor.fetchone()[0]))

                        cursor.execute("SELECT COUNT(*) FROM ui_settings")
                        self.sys_config_label.setText(str(cursor.fetchone()[0]))
                except Exception as e:
                    print(f"获取system统计失败: {e}")
            else:
                self.sys_size_label.setText("不存在")

        except Exception as e:
            print(f"刷新数据库信息失败: {e}")

    def _refresh_backup_list(self):
        """刷新备份列表"""
        # 清空列表
        while self.backup_list_layout.count():
            child = self.backup_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 扫描备份文件夹
        backup_dir = Path("备份")
        if not backup_dir.exists():
            backup_dir.mkdir(parents=True)

        backups = []
        total_size = 0

        for zip_file in backup_dir.glob("*.zip"):
            try:
                stat = zip_file.stat()
                size_mb = stat.st_size / (1024 * 1024)
                total_size += size_mb
                mtime = datetime.fromtimestamp(stat.st_mtime)

                backups.append({
                    'filename': zip_file.name,
                    'path': str(zip_file),
                    'time': mtime.strftime("%Y-%m-%d %H:%M"),
                    'size': f"{size_mb:.2f} MB",
                    'size_mb': size_mb,
                    'mtime': mtime
                })
            except Exception as e:
                print(f"读取备份文件失败: {e}")

        # 按时间排序（最新在前）
        backups.sort(key=lambda x: x['mtime'], reverse=True)

        # 更新统计
        self.backup_count_label.setText(f"{len(backups)} 个")
        self.backup_size_label.setText(f"{total_size:.2f} MB")

        if backups:
            self.last_backup_label.setText(backups[0]['time'])

        # 添加备份项
        if backups:
            for backup in backups[:20]:
                self._add_backup_item(backup)
        else:
            empty_label = QLabel("暂无备份文件")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet(f"color: {Colors.TEXT_MUTED_LIGHT}; padding: 40px;")
            self.backup_list_layout.addWidget(empty_label)

    def _get_backup_stats(self, backup_path: str) -> dict:
        """从备份文件获取统计信息"""
        stats = {
            'batch_count': 0,
            'barcode_count': 0,
            'scan_log_count': 0,
            'user_count': 0,
            'customer_count': 0,
        }

        try:
            import sqlite3

            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_dir)

                prod_db = Path(temp_dir) / "data/production.db"
                sys_db = Path(temp_dir) / "data/system.db"

                if prod_db.exists():
                    with sqlite3.connect(str(prod_db)) as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.execute("SELECT COUNT(*) FROM batches")
                            stats['batch_count'] = cursor.fetchone()[0]
                        except:
                            pass
                        try:
                            cursor.execute("SELECT COUNT(*) FROM barcodes")
                            stats['barcode_count'] = cursor.fetchone()[0]
                        except:
                            pass
                        try:
                            cursor.execute("SELECT COUNT(*) FROM scan_logs")
                            stats['scan_log_count'] = cursor.fetchone()[0]
                        except:
                            pass
                        try:
                            cursor.execute("SELECT COUNT(*) FROM customers")
                            stats['customer_count'] = cursor.fetchone()[0]
                        except:
                            pass

                if sys_db.exists():
                    with sqlite3.connect(str(sys_db)) as conn:
                        cursor = conn.cursor()
                        try:
                            cursor.execute("SELECT COUNT(*) FROM users")
                            stats['user_count'] = cursor.fetchone()[0]
                        except:
                            pass

        except Exception as e:
            print(f"获取备份统计失败: {e}")

        return stats

    def _backup_database(self):
        """备份数据库"""
        try:
            backup_dir = Path("备份")
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"backup_{timestamp}.zip"

            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if Path("data/production.db").exists():
                    zipf.write("data/production.db")
                if Path("data/system.db").exists():
                    zipf.write("data/system.db")

            self.show_message("成功", f"数据库已备份:\n{backup_path.name}", "info")
            self.refresh()

        except Exception as e:
            self.show_message("错误", f"备份失败: {e}", "error")

    def _on_restore_clicked(self, backup_info: dict, checked: bool = False):
        """恢复按钮点击事件处理（兼容 Cython 编译）"""
        self._restore_backup(backup_info)

    def _on_delete_clicked(self, path: str, checked: bool = False):
        """删除按钮点击事件处理（兼容 Cython 编译）"""
        self._delete_backup(path)

    def _restore_backup(self, backup_info: dict):
        """恢复备份 - 弹出确认对话框"""
        from ..dialogs.backup_restore_dialog import BackupRestoreDialog

        # 获取备份统计
        stats = self._get_backup_stats(backup_info['path'])

        dialog = BackupRestoreDialog(backup_info, stats, self)
        if dialog.exec():
            restore_prod, restore_sys = dialog.get_selections()
            self._execute_restore(backup_info['path'], restore_prod, restore_sys)

    def _execute_restore(self, backup_path: str, restore_prod: bool, restore_sys: bool):
        """执行恢复操作"""
        try:
            # 创建安全备份
            safety_dir = Path("备份") / "安全备份"
            safety_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if restore_prod and Path("data/production.db").exists():
                shutil.copy2("data/production.db", safety_dir / f"production_安全_{timestamp}.db")
            if restore_sys and Path("data/system.db").exists():
                shutil.copy2("data/system.db", safety_dir / f"system_安全_{timestamp}.db")

            # 关闭数据库连接
            self.db_manager.close_all()

            # 解压恢复
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_dir)

                temp_path = Path(temp_dir)
                Path("data").mkdir(exist_ok=True)

                if restore_prod and (temp_path / "data/production.db").exists():
                    if Path("data/production.db").exists():
                        Path("data/production.db").unlink()
                    shutil.copy2(temp_path / "data/production.db", "data/production.db")

                if restore_sys and (temp_path / "data/system.db").exists():
                    if Path("data/system.db").exists():
                        Path("data/system.db").unlink()
                    shutil.copy2(temp_path / "data/system.db", "data/system.db")

            restored = []
            if restore_prod:
                restored.append("生产数据库")
            if restore_sys:
                restored.append("系统数据库")

            self.show_message("成功", f"已恢复: {', '.join(restored)}\n请重启程序。", "info")

        except Exception as e:
            self.show_message("错误", f"恢复失败: {e}", "error")

    def _delete_backup(self, backup_path: str):
        """删除备份"""
        filename = Path(backup_path).name
        if not self.show_message("确认", f"确定要删除此备份吗？\n\n{filename}\n\n此操作不可恢复！", "question"):
            return

        try:
            Path(backup_path).unlink()
            self.show_message("成功", "备份已删除", "info")
            self.refresh()
        except Exception as e:
            self.show_message("错误", f"删除失败: {e}", "error")

    def _open_backup_folder(self):
        """打开备份文件夹"""
        backup_dir = Path("备份")
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            os.startfile(str(backup_dir.absolute()))
        except Exception as e:
            self.show_message("错误", f"打开文件夹失败: {e}", "error")

    def _clear_system_logs(self):
        """清理系统日志 - 三级确认"""
        # 统计日志数量
        try:
            with self.db_manager.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM system_logs")
                log_count = cursor.fetchone()[0]
        except:
            log_count = 0

        if log_count == 0:
            self.show_message("提示", "没有系统日志需要清理", "info")
            return

        # 第一级确认
        if not self.show_message("⚠️ 第一步确认", f"你确定要清理所有系统日志吗？\n\n共 {log_count} 条日志", "question"):
            return

        # 第二级确认
        if not self.show_message("🚨 第二步确认 - 后果警告",
            f"此操作将永久删除：\n\n• 系统日志：{log_count} 条\n\n删除后将无法恢复！\n你确定了解后果吗？", "warning"):
            return

        # 第三级确认
        if not self.show_message("💀 最后确认 - 不可撤销",
            "这是最后一次确认！\n\n点击「Yes」后数据将被永久删除！\n\n你真的、确定、一定要清理吗？", "critical"):
            return

        try:
            with self.db_manager.get_connection('system') as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM system_logs")
                conn.commit()
            self.show_message("成功", f"已清理 {log_count} 条系统日志", "info")
            self.refresh()
        except Exception as e:
            self.show_message("错误", f"清理失败: {e}", "error")

    def _clear_scan_logs(self):
        """清理扫描日志 - 三级确认"""
        # 统计日志数量
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM scan_logs")
                log_count = cursor.fetchone()[0]
        except:
            log_count = 0

        if log_count == 0:
            self.show_message("提示", "没有扫描日志需要清理", "info")
            return

        # 第一级确认
        if not self.show_message("⚠️ 第一步确认", f"你确定要清理所有扫描日志吗？\n\n共 {log_count} 条日志", "question"):
            return

        # 第二级确认
        if not self.show_message("🚨 第二步确认 - 后果警告",
            f"此操作将永久删除：\n\n• 扫描日志：{log_count} 条\n\n删除后将无法恢复！\n你确定了解后果吗？", "warning"):
            return

        # 第三级确认
        if not self.show_message("💀 最后确认 - 不可撤销",
            "这是最后一次确认！\n\n点击「Yes」后数据将被永久删除！\n\n你真的、确定、一定要清理吗？", "critical"):
            return

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM scan_logs")
                conn.commit()
            self.show_message("成功", f"已清理 {log_count} 条扫描日志", "info")
            self.refresh()
        except Exception as e:
            self.show_message("错误", f"清理失败: {e}", "error")

    def _clear_archived_batches(self):
        """清理归档批次 - 三级确认"""
        # 统计归档批次和条码数量
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM batches WHERE status = 2")
                batch_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM barcodes WHERE batch_id IN (SELECT id FROM batches WHERE status = 2)")
                barcode_count = cursor.fetchone()[0]
        except:
            batch_count = 0
            barcode_count = 0

        if batch_count == 0:
            self.show_message("提示", "没有归档批次需要清理", "info")
            return

        # 第一级确认
        if not self.show_message("⚠️ 第一步确认", f"你确定要清理所有归档批次吗？\n\n共 {batch_count} 个批次", "question"):
            return

        # 第二级确认
        if not self.show_message("🚨 第二步确认 - 后果警告",
            f"此操作将永久删除：\n\n• 归档批次：{batch_count} 个\n• 关联条码：{barcode_count} 条\n\n删除后将无法恢复！\n你确定了解后果吗？", "warning"):
            return

        # 第三级确认
        if not self.show_message("💀 最后确认 - 不可撤销",
            "这是最后一次确认！\n\n点击「Yes」后数据将被永久删除！\n\n你真的、确定、一定要清理吗？", "critical"):
            return

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM barcodes WHERE batch_id IN (SELECT id FROM batches WHERE status = 2)")
                cursor.execute("DELETE FROM batches WHERE status = 2")
                conn.commit()
            self.show_message("成功", f"已清理 {batch_count} 个归档批次和 {barcode_count} 条条码", "info")
            self.refresh()
        except Exception as e:
            self.show_message("错误", f"清理失败: {e}", "error")

    def _show_batch_manage_dialog(self):
        """显示批次管理对话框"""
        from ..dialogs.batch_manage_dialog import BatchManageDialog

        dialog = BatchManageDialog(self.db_manager, self)
        dialog.batches_deleted.connect(self._on_batches_deleted)
        dialog.exec()
        self.refresh()  # 刷新统计信息

    def _on_batches_deleted(self):
        """批次删除后刷新相关页面"""
        # 查找主窗口并刷新扫码验证页面和批次管理页面
        main_window = self.window()
        if main_window and hasattr(main_window, 'pages'):
            # 刷新扫码验证页面（强制重新加载批次选项卡）
            scan_page = main_window.pages.get("scan")
            if scan_page and hasattr(scan_page, 'force_refresh'):
                scan_page.force_refresh()
            # 刷新批次管理页面
            batch_page = main_window.pages.get("batch")
            if batch_page and hasattr(batch_page, 'refresh'):
                batch_page.refresh()

    def refresh(self):
        """刷新页面"""
        self._refresh_db_info()
        self._refresh_backup_list()
