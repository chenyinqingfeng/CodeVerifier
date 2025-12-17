"""
语音播报模块 - 扫码结果语音提示
使用 pygame 播放预录制的高质量语音文件（由 edge-tts 生成）
"""

import threading
import queue
import os
from typing import Optional
from PySide6.QtCore import QObject, Signal


class VoiceAnnouncer(QObject):
    """语音播报器 - 使用 pygame 播放预录音频"""

    # 播报完成信号
    announce_completed = Signal(str)

    # 音频文件映射（优先使用 wav，如果不存在则尝试 mp3）
    AUDIO_FILES = {
        "正面匹配": "front_matched",
        "反面匹配": "back_matched",
        "匹配成功": "match_success",
        "条码无效": "invalid_code",
        "重复扫码": "duplicate_scan",
        "二码不一致": "mismatch",
        "解锁条码错误": "lock_mismatch",
    }

    def __init__(self, ui_config=None):
        super().__init__()
        self._ui_config = ui_config
        self._queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._pygame_initialized = False

        # 音频文件目录
        self._audio_dir = self._get_audio_dir()

        # 延迟初始化 pygame（在后台线程中初始化，避免阻塞主线程）
        # 启动播报线程
        self._start_worker()

    def _get_audio_dir(self) -> str:
        """获取音频文件目录"""
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 音频文件在 resources/audio 目录
        audio_dir = os.path.join(current_dir, "..", "resources", "audio")
        return os.path.normpath(audio_dir)

    def _init_pygame(self):
        """初始化 pygame mixer"""
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._pygame_initialized = True
        except ImportError:
            pass
        except Exception as e:
            print(f"[VoiceAnnouncer] pygame 初始化失败: {e}")

    def _start_worker(self):
        """启动后台播报线程"""
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _worker_loop(self):
        """后台工作线程循环"""
        # 在后台线程中初始化 pygame，避免阻塞主线程
        self._init_pygame()

        while self._running:
            try:
                # 阻塞等待任务，超时1秒
                text = self._queue.get(timeout=1.0)

                if text is None:  # 退出信号
                    break

                # 执行播报
                self._do_play(text)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[VoiceAnnouncer] 播报异常: {e}")

    def _do_play(self, text: str):
        """实际执行音频播放"""
        if not self._pygame_initialized:
            self._init_pygame()
        if not self._pygame_initialized:
            return

        # 获取音频文件路径（优先wav，其次mp3）
        audio_base = self.AUDIO_FILES.get(text)
        if not audio_base:
            print(f"[VoiceAnnouncer] 未找到音频文件映射: {text}")
            return

        # 尝试 wav 和 mp3 格式
        audio_path = None
        for ext in ['.wav', '.mp3']:
            candidate = os.path.join(self._audio_dir, audio_base + ext)
            if os.path.exists(candidate):
                audio_path = candidate
                break

        if not audio_path:
            print(f"[VoiceAnnouncer] 音频文件不存在: {audio_base}.wav/.mp3")
            return

        repeat_count = self._get_repeat_count()
        volume = self._get_voice_volume()

        try:
            import pygame
            import time

            for i in range(repeat_count):
                # 加载并播放音频
                pygame.mixer.music.load(audio_path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play()

                # 等待播放完成
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                # 多次播报之间的间隔
                if i < repeat_count - 1:
                    time.sleep(0.3)

        except Exception as e:
            print(f"[VoiceAnnouncer] 播放失败: {e}")

    def _get_voice_volume(self) -> float:
        """获取音量配置（0.0-2.0，支持放大）"""
        if self._ui_config:
            config = self._ui_config.get_voice_config()
            return config.get('volume', 1.0)
        return 1.0

    def _get_repeat_count(self) -> int:
        """获取播报次数配置"""
        if self._ui_config:
            config = self._ui_config.get_voice_config()
            return config.get('repeat', 1)
        return 1

    def is_enabled(self) -> bool:
        """检查语音播报是否启用"""
        if self._ui_config:
            config = self._ui_config.get_voice_config()
            return config.get('enabled', True)
        return True

    def announce(self, text: str):
        """添加播报任务（异步）"""
        if not self.is_enabled():
            return

        if not text:
            return

        # 清空队列中的旧任务，只保留最新的
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

        self._queue.put(text)

    # ==================== 扫码结果播报方法 ====================

    def announce_front_matched(self):
        """播报：正面匹配"""
        self.announce("正面匹配")

    def announce_back_matched(self):
        """播报：反面匹配"""
        self.announce("反面匹配")

    def announce_match_success(self):
        """播报：匹配成功"""
        self.announce("匹配成功")

    def announce_invalid_code(self):
        """播报：条码无效"""
        self.announce("条码无效")

    def announce_duplicate_scan(self):
        """播报：重复扫码"""
        self.announce("重复扫码")

    def announce_mismatch(self):
        """播报：二码不一致"""
        self.announce("二码不一致")

    def announce_lock_mismatch(self):
        """播报：解锁条码错误（打印锁定模式下扫到不匹配的条码）"""
        self.announce("解锁条码错误")

    # ==================== 资源清理 ====================

    def cleanup(self):
        """清理资源"""
        self._running = False
        self._queue.put(None)  # 发送退出信号

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        # 清理 pygame
        if self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.quit()
            except:
                pass

        print("[VoiceAnnouncer] 已清理")


# 全局单例
_voice_announcer: Optional[VoiceAnnouncer] = None


def get_voice_announcer(ui_config=None) -> VoiceAnnouncer:
    """获取语音播报器单例"""
    global _voice_announcer
    if _voice_announcer is None:
        _voice_announcer = VoiceAnnouncer(ui_config)
    elif ui_config is not None:
        # 更新配置引用
        _voice_announcer._ui_config = ui_config
    return _voice_announcer


def cleanup_voice_announcer():
    """清理语音播报器"""
    global _voice_announcer
    if _voice_announcer:
        _voice_announcer.cleanup()
        _voice_announcer = None
