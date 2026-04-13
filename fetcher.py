"""
BabyBus 下载器 — 频道列表获取模块
用 yt-dlp 拉取频道视频元数据
"""

import subprocess
from config import SUBPROCESS_ENCODING
from utils import build_yt_dlp_cmd


def get_playlist_info(channel_url, run_logger=None):
    """
    获取频道全部视频信息，返回列表：
    [{id, title, upload_date, duration}, ...]
    """
    cmd = build_yt_dlp_cmd([
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s\t%(upload_date)s\t%(duration)s",
        channel_url,
    ])
    result = subprocess.run(cmd, capture_output=True, text=True, encoding=SUBPROCESS_ENCODING, errors='replace')
    if result.returncode != 0:
        print("获取频道列表失败:", result.stderr[:500])
        if run_logger:
            run_logger.log(result.stderr[:200])
        return []
    videos = []
    for line in result.stdout.strip().splitlines():
        if not line or line.startswith('{'):
            continue
        parts = line.split('\t')
        if len(parts) >= 1 and parts[0]:
            videos.append({
                "id": parts[0],
                "title": parts[1] if len(parts) > 1 else "",
                "upload_date": parts[2] if len(parts) > 2 else "",
                "duration": parts[3] if len(parts) > 3 else "",
            })
    print(f"获取到 {len(videos)} 个视频")
    if run_logger:
        run_logger.log(f"获取到 {len(videos)} 个视频")
    return videos
