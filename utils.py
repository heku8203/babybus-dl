"""
BabyBus 下载器 — 工具函数
ffmpeg/node 查找、yt-dlp 命令构建、时长格式化、emoji 清理
"""

import os
import re
import subprocess
import platform


def find_ffmpeg():
    """查找 ffmpeg 可执行文件路径"""
    win_paths = [
        r"C:\Users\heku8\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
    ]
    if platform.system() == "Windows":
        for p in win_paths:
            if os.path.exists(p):
                return p
    result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return "ffmpeg"


def find_node():
    """查找 Node.js 可执行文件路径"""
    win_paths = [
        r"C:\Program Files\nodejs\node.exe",
        os.path.expanduser(r"~\AppData\Roaming\npm\node.exe"),
    ]
    if platform.system() == "Windows":
        for p in win_paths:
            if os.path.exists(p):
                return p
    result = subprocess.run(["which", "node"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


# 启动时查找一次，后续复用
FFMPEG = find_ffmpeg()
NODE = find_node()
print(f"[初始化] ffmpeg: {FFMPEG}")
print(f"[初始化] node: {NODE}")


def build_yt_dlp_cmd(extra_opts=None):
    """返回 yt-dlp 命令列表，extra_opts 追加到末尾"""
    cmd = ["yt-dlp"]
    if FFMPEG != "ffmpeg" and os.path.exists(FFMPEG):
        cmd.append(f"--ffmpeg-location={os.path.dirname(FFMPEG)}")
    if NODE and os.path.exists(NODE):
        cmd.append(f"--js-runtimes=node:{os.path.dirname(NODE)}")
    if extra_opts:
        cmd.extend(extra_opts)
    return cmd


def format_duration(seconds_str):
    """秒数转 HH:MM:SS 或 M:SS 字符串"""
    try:
        s = int(float(seconds_str))
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h}:{m:02d}:{sec:02d}" if h > 0 else f"{m}:{sec:02d}"
    except Exception:
        return seconds_str


def remove_emoji(text):
    """移除字符串中的 emoji 字符"""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F" u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF" u"\U0001F1E0-\U0001F1FF"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)
