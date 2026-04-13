"""
BabyBus 下载器 — 视频下载模块
用 yt-dlp 下载单个视频
"""

import os
import subprocess
from config import SUBPROCESS_ENCODING
from utils import build_yt_dlp_cmd


def download_video(video_id, path, run_logger=None):
    """
    下载单个视频，返回 (returncode, filename, filesize_mb)
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"下载: {video_id}")

    cmd = build_yt_dlp_cmd([
        "-f", "best",
        "-P", path,
        "--no-playlist",
        "--merge-output-format", "mp4",
        url,
    ])
    result = subprocess.run(cmd, capture_output=True, text=True, encoding=SUBPROCESS_ENCODING, errors='replace')

    if result.returncode != 0:
        err_lines = result.stderr.strip().splitlines()
        err_msg = err_lines[-1] if err_lines else "未知错误"
        print(f"下载失败: {video_id} | {err_msg}")
        if run_logger:
            run_logger.log(f"下载失败: {video_id}")
        return 1, "", 0.0

    # 查找已下载的文件
    actual_files = [
        f for f in os.listdir(path)
        if video_id in f and (f.endswith('.mp4') or f.endswith('.webm'))
    ]
    if actual_files:
        actual_path = os.path.join(path, actual_files[0])
        size_mb = os.path.getsize(actual_path) / (1024 * 1024)
        print(f"下载完成: {video_id}" + (f" ({size_mb:.1f}MB)" if size_mb else ""))
        if run_logger:
            run_logger.log(f"下载完成: {video_id}")
        return 0, actual_path, round(size_mb, 2)
    else:
        print(f"下载失败: {video_id} | 文件未找到")
        if run_logger:
            run_logger.log(f"下载失败: {video_id}")
        return 1, "", 0.0
