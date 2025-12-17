"""
条码打印模块 - PySide6版本
负责条码生成和打印

移植自老版本ctk的条码打印逻辑，支持：
- 以"毫米"为基准，输出严格的物理尺寸
- 默认标签尺寸：70mm × 20mm
- CODE39/CODE128 两种条码类型
"""

from typing import Optional, Callable, List, Dict, Any
from PySide6.QtCore import QObject, Signal

# 可选依赖导入
try:
    from PIL import Image, ImageDraw, ImageFont, ImageWin
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = ImageDraw = ImageFont = ImageWin = None

try:
    import win32print, win32ui
    from win32.lib import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    win32print = win32ui = win32con = None

try:
    from barcode import Code39, Code128
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    Code39 = Code128 = ImageWriter = None


def generate_barcode_image_simple(code: str, barcode_type: str = "CODE128", dpi: int = 150) -> Optional["Image.Image"]:
    """
    独立的条码生成函数，供前端UI使用
    返回PIL图像对象，适合在预览区显示
    """
    if not BARCODE_AVAILABLE or not PIL_AVAILABLE:
        return None

    try:
        # 清理条码内容
        if barcode_type == "CODE128":
            # Code128支持ASCII 0-127的所有字符
            clean_code = "".join(ch for ch in (code or "").strip() if ord(ch) >= 32 and ord(ch) <= 126)
        else:
            # Code39字符集
            valid = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $+/%*")
            clean_code = "".join(ch for ch in (code or "").upper().strip() if ch in valid)

        if not clean_code:
            return None

        # 使用python-barcode生成
        writer = ImageWriter()
        writer_options = {
            "dpi": dpi,
            "module_width": 0.33,  # 适合屏幕显示的模块宽度
            "module_height": 20.0,    # 条码高度
            "quiet_zone": 6.5,       # 静默区
            "write_text": False,      # 不绘制文字
            "background": "white",
            "foreground": "black",
        }

        # 生成条码
        if barcode_type == "CODE128":
            barcode_obj = Code128(clean_code, writer=writer)
        else:
            barcode_obj = Code39(clean_code, writer=writer, add_checksum=False)

        barcode_image = barcode_obj.render(writer_options)

        # 确保有合适的高度
        if barcode_image.height < 40:
            target_height = 40
            barcode_image = barcode_image.resize(
                (barcode_image.width, target_height),
                Image.NEAREST
            )

        return barcode_image

    except Exception as e:
        print(f"独立条码生成失败: {e}")
        return None


class BarcodePrinter(QObject):
    """条码打印器（移植自老版本ctk）"""

    # Qt信号
    print_completed = Signal(str, bool)  # (barcode, success)
    printer_status_changed = Signal(bool)  # is_available

    def __init__(self, ui_config=None):
        super().__init__()
        self._ui_config = ui_config
        self._log_callback: Optional[Callable] = None

        # 打印配置（默认值，与老版本一致）
        self._enabled = True
        self._selected_printer: Optional[str] = None
        self._label_width = 70.0      # mm
        self._label_height = 20.0     # mm
        self._barcode_width = 0.25    # mm - 条码模块基础宽度
        self._barcode_height = 10.0   # mm - 条码高度
        self._top_margin = 2.0        # mm - 条码距离标签顶部边距
        self._text_gap = -1.0         # mm - 文字距离条码的纵向间距（负值表示重叠）
        self._font_size = 12          # pt
        self._font_name = "Arial"
        self._barcode_type = "CODE39"  # CODE39 或 CODE128
        self._auto_print_repeat_count = 1  # 自动重复打印次数

        # 缩放补偿系数（基于实际测试结果，与老版本一致）
        self._width_scale = 0.948
        self._height_scale = 1.163

        # 状态变量
        self.current_print_code: Optional[str] = None   # 当前准备打印的条码
        self.last_printed_code: Optional[str] = None    # 上次已打印完成的条码

        # DPI缓存
        self._cached_dpi: Optional[tuple] = None
        self._dpi_cache_printer: Optional[str] = None

        # 加载配置
        self._load_config()

    def set_log_callback(self, callback: Callable):
        """设置日志回调"""
        self._log_callback = callback

    def _log(self, message: str):
        """记录日志"""
        if self._log_callback:
            self._log_callback(message)
        print(message)

    def _load_config(self):
        """从配置加载打印设置"""
        if not self._ui_config:
            return

        config = self._ui_config.get_print_config()
        self._enabled = config.get('enabled', True)
        self._selected_printer = config.get('printer_name')
        self._label_width = config.get('label_width', 70.0)
        self._label_height = config.get('label_height', 20.0)
        self._barcode_width = config.get('barcode_width', 0.25)
        self._barcode_height = config.get('barcode_height', 10.0)
        self._top_margin = config.get('barcode_top_margin', 2.0)
        self._text_gap = config.get('text_gap', -1.0)
        self._font_size = config.get('font_size', 12)
        self._barcode_type = config.get('barcode_type', 'CODE39')

    def update_config(self, config: Dict[str, Any]):
        """更新打印配置"""
        if 'enabled' in config:
            self._enabled = config['enabled']
        if 'printer_name' in config:
            self._selected_printer = config['printer_name']
            self._cached_dpi = None
        if 'label_width' in config:
            self._label_width = float(config['label_width'])
        if 'label_height' in config:
            self._label_height = float(config['label_height'])
        if 'barcode_width' in config:
            self._barcode_width = float(config['barcode_width'])
        if 'barcode_height' in config:
            self._barcode_height = float(config['barcode_height'])
        if 'barcode_top_margin' in config:
            self._top_margin = float(config['barcode_top_margin'])
        if 'text_gap' in config:
            self._text_gap = float(config['text_gap'])
        if 'font_size' in config:
            self._font_size = int(config['font_size'])
        if 'font_name' in config:
            self._font_name = str(config['font_name'])
        if 'barcode_type' in config:
            self._barcode_type = config['barcode_type']
        if 'auto_print_repeat_count' in config:
            self._auto_print_repeat_count = int(config['auto_print_repeat_count'])

    def get_auto_print_repeat_count(self) -> int:
        """获取自动重复打印次数"""
        return self._auto_print_repeat_count

    def set_auto_print_repeat_count(self, count: int):
        """设置自动重复打印次数"""
        self._auto_print_repeat_count = max(1, min(10, count))  # 限制 1-10

    # ==================== 状态检查 ====================

    def is_available(self) -> bool:
        """检查打印功能是否可用"""
        return PIL_AVAILABLE and WIN32_AVAILABLE and BARCODE_AVAILABLE

    def is_enabled(self) -> bool:
        """检查打印是否启用"""
        return self._enabled and self.is_available() and self._selected_printer is not None

    def set_enabled(self, enabled: bool):
        """设置打印启用状态"""
        self._enabled = enabled

    def get_selected_printer(self) -> Optional[str]:
        """获取选中的打印机"""
        return self._selected_printer

    def set_selected_printer(self, printer: str):
        """设置打印机"""
        self._selected_printer = printer

    @staticmethod
    def list_printers() -> List[str]:
        """列出所有可用打印机"""
        if not WIN32_AVAILABLE:
            return []

        try:
            printers = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            return [p[2] for p in printers]
        except Exception:
            return []

    # ==================== 打印功能 ====================

    def print_barcode(self, barcode: str, force: bool = False, repeat_count: int = None) -> bool:
        """
        打印条码

        Args:
            barcode: 要打印的条码内容
            force: 是否强制打印（忽略启用状态）
            repeat_count: 重复打印次数，None 表示使用配置值

        Returns:
            是否打印成功
        """
        if not force and not self.is_enabled():
            self._log(f"[INFO] 打印功能未启用，跳过打印: {barcode}")
            return False

        if not self._selected_printer:
            self._log(f"[ERROR] 未选择打印机，无法打印: {barcode}")
            self.print_completed.emit(barcode, False)
            return False

        if not self.is_available():
            self._log(f"[ERROR] 打印依赖库不可用")
            self.print_completed.emit(barcode, False)
            return False

        # 确定打印次数
        actual_repeat = repeat_count if repeat_count is not None else self._auto_print_repeat_count
        actual_repeat = max(1, min(10, actual_repeat))  # 限制 1-10

        try:
            # 获取打印机DPI
            dpi_x, dpi_y = self._get_printer_dpi()

            # 生成条码图像
            image = self._generate_barcode_image(barcode, dpi_x, dpi_y)
            if image is None:
                self._log(f"[ERROR] 生成条码图像失败: {barcode}")
                self.print_completed.emit(barcode, False)
                return False

            # 执行打印（支持重复打印）
            all_success = True
            for i in range(actual_repeat):
                success = self._print_image(image)
                if not success:
                    all_success = False
                    self._log(f"[ERROR] 条码打印失败 (第{i+1}/{actual_repeat}次): {barcode}")
                    break
                if actual_repeat > 1:
                    self._log(f"[OK] 条码打印成功 (第{i+1}/{actual_repeat}次): {barcode}")

            if all_success:
                if actual_repeat == 1:
                    self._log(f"[OK] 条码打印成功: {barcode}")
                else:
                    self._log(f"[OK] 条码重复打印完成 ({actual_repeat}次): {barcode}")
            else:
                self._log(f"[ERROR] 条码打印失败: {barcode}")

            self.print_completed.emit(barcode, all_success)
            return all_success

        except Exception as e:
            self._log(f"[ERROR] 打印异常: {e}")
            self.print_completed.emit(barcode, False)
            return False

    def _get_printer_dpi(self) -> tuple:
        """获取打印机DPI"""
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(self._selected_printer or "")
            dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
            dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)
            hdc.DeleteDC()
            return (dpi_x, dpi_y)
        except Exception:
            return (300, 300)  # 默认DPI

    def _mm_to_px(self, mm: float, dpi: int) -> int:
        """精确毫米到像素转换，避免浮点累积误差"""
        return int(round(mm / 25.4 * dpi))

    # ==================== 条码内容处理 ====================

    def sanitize_code_for_code39(self, code: str) -> str:
        """处理条码内容，确保 Code39 兼容性"""
        try:
            s = (code or "").upper().strip()
            valid = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $+/%*")
            return "".join(ch for ch in s if ch in valid)
        except Exception as e:
            self._log(f"Code39清理异常: {e}")
            return ""

    def sanitize_code_for_code128(self, code: str) -> str:
        """处理条码内容，确保 Code128 兼容性"""
        try:
            s = (code or "").strip()
            # Code128支持ASCII 0-127的所有字符，这里只过滤非打印字符
            return "".join(ch for ch in s if ord(ch) >= 32 and ord(ch) <= 126)
        except Exception as e:
            self._log(f"Code128清理异常: {e}")
            return ""

    def sanitize_code(self, code: str) -> str:
        """根据当前选择的条码类型处理条码内容"""
        try:
            if not code:
                return ""

            if self._barcode_type == "CODE128":
                return self.sanitize_code_for_code128(code)
            else:
                return self.sanitize_code_for_code39(code)

        except Exception as e:
            self._log(f"条码清理异常: {e}")
            return ""

    # ==================== 条码图像生成（移植自老版本） ====================

    def generate_barcode_image(self, code: str, dpi_x: int = 600, dpi_y: int = 600) -> Optional["Image.Image"]:
        """
        严格按毫米为基准生成条码图像，条码与文字分离绘制，杜绝拉伸变形
        移植自老版本ctk
        """
        if Code39 is None or not PIL_AVAILABLE:
            return None
        try:
            # ---- 严格的物理尺寸定义（mm），应用缩放补偿系数 ----
            LABEL_W_MM = float(self._label_width)    # 70.0
            LABEL_H_MM = float(self._label_height)   # 20.0
            TOP_MARGIN_MM = float(self._top_margin)  # 上边距（用户可配置）
            BOT_MARGIN_MM = 2.0                      # 下边距

            # 应用缩放补偿系数
            compensated_width = float(self._barcode_width) * self._width_scale
            compensated_height = float(self._barcode_height) * self._height_scale

            QUIET_ZONE_MM = max(10.0 * compensated_width, 2.5)  # Code39: 静默区>=10X，至少2.5mm
            BARCODE_H_MM = compensated_height  # 条码高度（已补偿）
            TEXT_GAP_MM = float(self._text_gap)      # 条码文字间距（用户配置）
            TEXT_HEIGHT_MM = 6.5                     # 文字区域高度

            # 精确像素计算
            img_width_px = self._mm_to_px(LABEL_W_MM, dpi_x)
            img_height_px = self._mm_to_px(LABEL_H_MM, dpi_y)

            # 创建白色画布
            canvas = Image.new("RGB", (img_width_px, img_height_px), "white")

            # 条码数据预处理
            barcode_data = self.sanitize_code(code)
            if not barcode_data:
                return None

            # === 条码绘制区域 ===
            self._draw_barcode_section(canvas, barcode_data,
                                      LABEL_W_MM, QUIET_ZONE_MM, BARCODE_H_MM,
                                      TOP_MARGIN_MM, dpi_x, dpi_y)

            # === 文字绘制区域 ===
            self._draw_text_section(canvas, barcode_data,
                                   LABEL_W_MM, BARCODE_H_MM, TEXT_GAP_MM,
                                   TEXT_HEIGHT_MM, TOP_MARGIN_MM, BOT_MARGIN_MM,
                                   dpi_x, dpi_y)

            return canvas

        except Exception as e:
            self._log(f"条码打印: 生成条码图片失败 - {e}")
            return None

    def _draw_barcode_section(self, canvas: "Image.Image", data: str,
                             label_w_mm: float, quiet_mm: float, bar_h_mm: float,
                             top_mm: float, dpi_x: int, dpi_y: int):
        """绘制条码部分，严格控制尺寸不被拉伸"""
        try:
            # 计算条码可用宽度
            usable_w_mm = label_w_mm - 2 * quiet_mm

            # 根据条码类型计算模块数量
            char_count = len(data)
            if self._barcode_type == "CODE128":
                # Code128模块计算：起始符3模块+数据+校验符+停止符2模块+终止条2模块
                # 每字符大约11模块（简化计算）
                total_modules = 3 + char_count * 11 + 1 + 2 + 2
            else:
                # Code39模块计算：每字符13模块+字符间1模块+起止符
                total_modules = (char_count + 2) * 13 + (char_count + 1) * 1

            # 动态计算模块宽度，应用缩放补偿系数
            calculated_module_w = usable_w_mm / total_modules
            # 使用补偿后的宽度作为基础宽度
            compensated_width = self._barcode_width * self._width_scale
            module_w_mm = compensated_width
            if (total_modules * module_w_mm) > usable_w_mm:
                module_w_mm = calculated_module_w

            # 使用python-barcode生成原始条码
            writer = ImageWriter()
            writer_options = {
                "dpi": dpi_x,
                "module_width": module_w_mm,
                "module_height": bar_h_mm,
                "quiet_zone": quiet_mm,
                "write_text": False,  # 条码库不绘制文字
                "background": "white",
                "foreground": "black",
            }

            # 根据条码类型选择生成器
            if self._barcode_type == "CODE128":
                barcode_obj = Code128(data, writer=writer)
            else:
                barcode_obj = Code39(data, writer=writer, add_checksum=False)

            barcode_img = barcode_obj.render(writer_options)

            # 确保条码高度精确
            target_h_px = self._mm_to_px(bar_h_mm, dpi_y)
            if abs(barcode_img.height - target_h_px) > 1:
                barcode_img = barcode_img.resize((barcode_img.width, target_h_px),
                                                Image.NEAREST)  # 避免抗锯齿

            # 居中粘贴条码
            paste_x = (canvas.width - barcode_img.width) // 2
            paste_y = self._mm_to_px(top_mm, dpi_y)
            canvas.paste(barcode_img, (paste_x, paste_y))

        except Exception as e:
            self._log(f"条码绘制失败: {e}")

    def _draw_text_section(self, canvas: "Image.Image", data: str,
                          label_w_mm: float, bar_h_mm: float, text_gap_mm: float,
                          text_h_mm: float, top_mm: float, bot_mm: float,
                          dpi_x: int, dpi_y: int):
        """绘制文字部分，与条码分离处理"""
        try:
            draw = ImageDraw.Draw(canvas)

            # 字体大小计算（优先用配置的 pt；否则由毫米换算）
            font_pt = int(self._font_size) if self._font_size else int(round(text_h_mm / 0.3528))  # 1pt ≈ 0.3528mm

            # 字体加载
            font = self._load_font(font_pt, dpi_y)

            # 文字定位
            text_bbox = draw.textbbox((0, 0), data, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]

            # 水平居中
            text_x = (canvas.width - text_w) // 2

            # 垂直位置：条码下方+间距（支持负间距让文字重叠在条码上）
            text_y_original = (self._mm_to_px(top_mm + bar_h_mm + text_gap_mm, dpi_y))
            text_y = text_y_original

            # 如果间距为负值，允许文字覆盖在条码区域
            if text_gap_mm >= 0:
                # 正间距：边界检查，确保不超出底边距
                bottom_limit = canvas.height - self._mm_to_px(bot_mm, dpi_y)
                if text_y + text_h > bottom_limit:
                    text_y = bottom_limit - text_h

            # 绘制文字
            draw.text((text_x, text_y), data, font=font, fill="black")

        except Exception as e:
            self._log(f"文字绘制失败: {e}")

    def _load_font(self, size_pt: int, dpi_y: int) -> "ImageFont.ImageFont":
        """加载字体（把 pt 转像素：px = pt * dpi/72），保证不同 DPI 下物理大小一致"""
        try:
            px = max(5, int(round(size_pt * (dpi_y / 72.0))))
        except Exception:
            px = max(5, int(size_pt))
        for font_name in ["Arial.ttf", "arial.ttf", "calibri.ttf", "Calibri.ttf"]:
            try:
                return ImageFont.truetype(font_name, px)
            except Exception:
                continue
        # 兜底
        try:
            return ImageFont.load_default()
        except Exception:
            raise

    # ==================== 预览功能 ====================

    def generate_preview_image(self, code: str) -> Optional["Image.Image"]:
        """
        生成条码预览图像，按实际物理尺寸自适应显示
        """
        if not BARCODE_AVAILABLE or not PIL_AVAILABLE or not code:
            return None

        try:
            # 生成实际尺寸的条码图像（适中的DPI保证清晰度和大小平衡）
            preview_dpi = 200
            actual_image = self.generate_barcode_image(code, dpi_x=preview_dpi, dpi_y=preview_dpi)

            if actual_image is None:
                return None

            return actual_image

        except Exception as e:
            self._log(f"条码预览: 生成预览图像失败 - {e}")
            return None

    # ==================== 旧版兼容方法 ====================

    def _generate_barcode_image(self, code: str, dpi_x: int, dpi_y: int) -> Optional["Image.Image"]:
        """旧版方法，转发到新方法"""
        return self.generate_barcode_image(code, dpi_x, dpi_y)

    def _print_image(self, image: "Image.Image") -> bool:
        """打印图像"""
        hdc = None
        try:
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(self._selected_printer or "")

            # 获取打印机DPI
            printer_dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
            printer_dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)

            # 计算目标尺寸
            label_px_w = self._mm_to_px(self._label_width, printer_dpi_x)
            label_px_h = self._mm_to_px(self._label_height, printer_dpi_y)

            # 调整图像尺寸
            if image.size != (label_px_w, label_px_h):
                image = image.resize((label_px_w, label_px_h), Image.NEAREST)

            # 获取可打印区域
            printable_w = hdc.GetDeviceCaps(win32con.HORZRES)
            printable_h = hdc.GetDeviceCaps(win32con.VERTRES)

            # 居中打印
            print_x = (printable_w - label_px_w) // 2
            print_y = (printable_h - label_px_h) // 2

            # 开始打印
            hdc.StartDoc("条码打印")
            hdc.StartPage()
            hdc.SetMapMode(win32con.MM_TEXT)

            # 绘制图像
            dib = ImageWin.Dib(image)
            target_rect = (print_x, print_y, print_x + label_px_w, print_y + label_px_h)
            dib.draw(hdc.GetHandleOutput(), target_rect)

            hdc.EndPage()
            hdc.EndDoc()

            return True

        except Exception as e:
            self._log(f"[ERROR] 打印失败: {e}")
            return False

        finally:
            if hdc:
                try:
                    hdc.DeleteDC()
                except Exception:
                    pass


# 全局单例
barcode_printer = BarcodePrinter()
