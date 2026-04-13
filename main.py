"""
BabyBus 下载器 — 入口
编排全流程：获取列表 → 对比历史 → 下载 → 重命名 → 分类移动
支持定时循环运行（Docker 长驻）
"""

import os
import sys
import time
import signal
import platform

from config import (YTWEB, DOWNLOAD_PATH, DST_PATH,
                    CHANNEL_IDS_FILE, MAX_DOWNLOADS_PER_RUN,
                    SLEEP_INTERVAL, VERSION)
from fetcher import get_playlist_info
from downloader import download_video
from mover import chagname, move_files
from logger import RunLogger
from utils import format_duration
from database import (
    is_downloaded, upsert_video, log_download, migrate_from_csv, get_all_videos
)

# ===== 优雅退出 =====
_running = True

def _signal_handler(sig, frame):
    global _running
    print(f"\n收到信号 {sig}，等待当前任务完成后退出...")
    _running = False

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def compare_channel(prev_map, new_map, run_logger):
    """对比频道变化：新增 / 下架"""
    prev_ids = set(prev_map.keys())
    new_ids = set(new_map.keys())

    if not prev_ids:
        print(f"\n首次记录频道列表，共 {len(new_ids)} 个视频")
        run_logger.log(f"首次记录频道列表，共 {len(new_ids)} 个视频")
        return

    added = new_ids - prev_ids
    removed = prev_ids - new_ids
    print(f"\n频道对比（上轮 {len(prev_ids)} 个 → 本轮 {len(new_ids)} 个）：")
    run_logger.log(f"频道对比（上轮 {len(prev_ids)} 个 → 本轮 {len(new_ids)} 个）")

    if added:
        print(f"  新增视频：{len(added)} 个")
        run_logger.log(f"新增视频：{len(added)} 个")
        for vid in sorted(added):
            info = new_map[vid]
            dur = format_duration(info["duration"])
            print(f"    + {vid} | {info['title'][:40]} | {dur} | {info['upload_date']}")
            run_logger.log(f"  + {vid} | {info['title'][:40]} | {dur} | {info['upload_date']}")
    if removed:
        print(f"  已下架：{len(removed)} 个")
        run_logger.log(f"已下架：{len(removed)} 个")
        for vid in sorted(removed):
            info = prev_map[vid]
            print(f"    - {vid} | {info['title'][:40]} | {info['upload_date']}")
    if not added and not removed:
        print("  频道无变化")
        run_logger.log("频道无变化")


def save_channel_snapshot(playlist):
    """保存频道视频列表快照到 SQLite"""
    for v in playlist:
        dur_fmt = format_duration(v["duration"])
        dur_sec = v.get("duration", 0) or 0
        upsert_video(v["id"], v["title"], v.get("upload_date",""),
                     dur_fmt, float(dur_sec))


def run_once():
    """执行一次完整下载流程"""
    print(f"=== BabyBus 下载器 ===")
    print(f"频道: {YTWEB}")
    print(f"下载目录: {DOWNLOAD_PATH}")
    print(f"存放目录: {DST_PATH}")
    print(f"平台: {platform.system()}")

    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    run_logger = RunLogger()

    # 1. 获取频道视频列表
    playlist = get_playlist_info(YTWEB, run_logger)

    # 2. 对比频道历史（从 DB 读上轮快照）
    prev_map = {}
    for row in get_all_videos():
        prev_map[row["id"]] = {
            "title": row.get("title") or "",
            "upload_date": row.get("upload_date") or "",
            "duration": row.get("duration_sec") or 0,
        }
    new_map = {v["id"]: v for v in playlist}
    compare_channel(prev_map, new_map, run_logger)

    # 3. 保存快照到 DB
    save_channel_snapshot(playlist)

    # 4. 增量下载
    downloaded_count = 0

    for v in playlist:
        if downloaded_count >= MAX_DOWNLOADS_PER_RUN:
            print(f"\n已达到本次运行下载限制 ({MAX_DOWNLOADS_PER_RUN} 个)，停止下载")
            run_logger.log(f"达到下载限制 {MAX_DOWNLOADS_PER_RUN}，停止")
            break

        vid = v["id"]
        if is_downloaded(vid):
            print(f"已下载，跳过: {vid}")
            continue

        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        title_short = v["title"][:60] if v["title"] else ""
        print(f"开始下载: {vid} | {title_short}")
        run_logger.log(vid)

        rc, filepath, size_mb = download_video(vid, DOWNLOAD_PATH, run_logger)
        if rc == 0:
            downloaded_count += 1
            print('本地数据已更新')
            run_logger.log('已下载')
            fname = os.path.basename(filepath)
            dur_fmt = format_duration(v["duration"])
            log_download(vid, title_short, v.get("upload_date",""),
                        dur_fmt, size_mb, fname, status="ok")
        else:
            log_download(vid, title_short, v.get("upload_date",""),
                        "FAILED", 0.0, "", status="failed")

    # 5. 重命名 + 分类移动（传入 channel_file 做智能分类）
    chagname(DOWNLOAD_PATH, run_logger)
    move_files(DOWNLOAD_PATH, DST_PATH, channel_file=CHANNEL_IDS_FILE)
    print("全部完成:", run_logger.logs)


def run_single(video_id):
    """下载单个视频并处理"""
    print(f"=== BabyBus 单视频下载 ===")
    print(f"视频ID: {video_id}")
    print(f"下载目录: {DOWNLOAD_PATH}")
    print(f"存放目录: {DST_PATH}")

    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    run_logger = RunLogger()

    # 下载
    print(f"\n[1/3] 下载视频...")
    rc, filepath, size_mb = download_video(video_id, DOWNLOAD_PATH, run_logger)
    if rc != 0:
        print(f"下载失败: {video_id}")
        return False

    print(f"下载成功: {filepath} ({size_mb}MB)")

    # 重命名
    print(f"\n[2/3] 重命名...")
    chagname(DOWNLOAD_PATH, run_logger)

    # 分类移动
    print(f"\n[3/3] 分类移动...")
    move_files(DOWNLOAD_PATH, DST_PATH, channel_file=CHANNEL_IDS_FILE)

    print(f"\n完成: {video_id}")
    return True


if __name__ == '__main__':
    print(f"BabyBus 下载器 v{VERSION}")
    print(f"定时间隔: {SLEEP_INTERVAL}s ({SLEEP_INTERVAL // 3600}h)")
    print(f"PID: {os.getpid()}")
    migrate_from_csv()
    print()

    # 检查命令行参数
    if len(sys.argv) >= 3 and sys.argv[1] in ('--video', '-v'):
        video_id = sys.argv[2]
        run_single(video_id)
        sys.exit(0)

    while _running:
        try:
            run_once()
        except Exception as e:
            print(f"运行异常: {e}")

        if SLEEP_INTERVAL <= 0:
            break
        if not _running:
            break

        next_time = time.strftime("%H:%M:%S", time.localtime(time.time() + SLEEP_INTERVAL))
        print(f"\n下次运行: {next_time} ({SLEEP_INTERVAL}s 后)")
        print(f"等待中... (PID {os.getpid()}, 发送 SIGTERM 停止)")

        for _ in range(SLEEP_INTERVAL):
            if not _running:
                break
            time.sleep(1)

    print("已退出")
