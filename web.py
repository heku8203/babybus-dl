"""
BabyBus 下载器 — Web 管理界面
FastAPI + Jinja2，嵌入式单页应用
"""

import os
import asyncio
import json
import platform
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from web_templates import _render

from config import (
    VERSION, YTWEB, DOWNLOAD_PATH, DST_PATH, LOG_FILE,
    ID_LOG_FILE, CHANNEL_IDS_FILE, MAX_DOWNLOADS_PER_RUN,
    SLEEP_INTERVAL, LOGS_DIR
)
from fetcher import get_playlist_info
from downloader import download_video
from mover import chagname, move_files
from logger import RunLogger, write_csv_row
from utils import format_duration

# ============ 全局状态 ============
_app_state = {
    "running": False,
    "current_task": None,
    "last_run": None,
    "last_result": None,
    "logs": [],
    "max_log_lines": 500,
}

def _log(msg: str):
    """记录到内存日志"""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    _app_state["logs"].append(line)
    if len(_app_state["logs"]) > _app_state["max_log_lines"]:
        _app_state["logs"] = _app_state["logs"][-_app_state["max_log_lines"]:]
    print(line)

# ============ FastAPI 应用 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    _log(f"Web UI 启动 v{VERSION}")
    yield
    _log("Web UI 关闭")

app = FastAPI(title="BabyBus 下载器", version=VERSION, lifespan=lifespan)

# ============ 辅助函数 ============

def load_downloaded_ids() -> set:
    """加载已下载的 ID 集合"""
    if not os.path.exists(ID_LOG_FILE):
        return set()
    try:
        with open(ID_LOG_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except:
        return set()

def load_channel_data() -> list:
    """加载频道视频列表"""
    if not os.path.exists(CHANNEL_IDS_FILE):
        return []
    videos = []
    try:
        with open(CHANNEL_IDS_FILE, 'r', encoding='utf-8') as f:
            next(f, None)  # skip header
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    videos.append({
                        "id": parts[0],
                        "title": parts[1].strip('"'),
                        "upload_date": parts[2],
                        "duration_fmt": parts[3],
                        "duration_sec": parts[4],
                    })
    except Exception as e:
        _log(f"加载频道数据失败: {e}")
    return videos

def get_output_files() -> list:
    """获取 output 目录文件列表"""
    files = []
    if not os.path.exists(DST_PATH):
        return files
    for root, dirs, filenames in os.walk(DST_PATH):
        for f in filenames:
            if f.endswith(('.mp4', '.webm', '.mkv')):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, DST_PATH)
                category = os.path.dirname(rel_path) or "未分类"
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                files.append({
                    "name": f,
                    "category": category,
                    "path": rel_path,
                    "size_mb": round(size_mb, 2),
                    "mtime": datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M"),
                })
    return sorted(files, key=lambda x: x["mtime"], reverse=True)

# ============ 后台任务 ============

async def run_download_task(video_id: Optional[str] = None):
    """后台执行下载任务"""
    if _app_state["running"]:
        return {"error": "已有任务在运行"}
    
    _app_state["running"] = True
    _app_state["current_task"] = video_id or "频道扫描"
    _app_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        if video_id:
            # 单视频下载
            _log(f"开始单视频下载: {video_id}")
            os.makedirs(DOWNLOAD_PATH, exist_ok=True)
            run_logger = RunLogger()
            
            rc, filepath, size_mb = download_video(video_id, DOWNLOAD_PATH, run_logger)
            if rc == 0:
                _log(f"下载成功: {filepath} ({size_mb}MB)")
                chagname(DOWNLOAD_PATH, run_logger)
                move_files(DOWNLOAD_PATH, DST_PATH, channel_file=CHANNEL_IDS_FILE)
                _log("重命名和移动完成")
                _app_state["last_result"] = {"success": True, "video_id": video_id, "size_mb": size_mb}
            else:
                _log(f"下载失败: {video_id}")
                _app_state["last_result"] = {"success": False, "video_id": video_id, "error": "下载失败"}
        else:
            # 频道扫描（简化版，只下载 1 个测试）
            _log("开始频道扫描...")
            run_logger = RunLogger()
            playlist = get_playlist_info(YTWEB, run_logger)
            _log(f"获取到 {len(playlist)} 个视频")
            
            downloaded_ids = load_downloaded_ids()
            new_videos = [v for v in playlist if v["id"] not in downloaded_ids][:1]
            
            if new_videos:
                v = new_videos[0]
                _log(f"下载新视频: {v['id']}")
                rc, filepath, size_mb = download_video(v["id"], DOWNLOAD_PATH, run_logger)
                if rc == 0:
                    chagname(DOWNLOAD_PATH, run_logger)
                    move_files(DOWNLOAD_PATH, DST_PATH, channel_file=CHANNEL_IDS_FILE)
                    _app_state["last_result"] = {"success": True, "video_id": v["id"], "title": v["title"][:50]}
                else:
                    _app_state["last_result"] = {"success": False, "error": "下载失败"}
            else:
                _log("没有新视频")
                _app_state["last_result"] = {"success": True, "message": "没有新视频"}
                
    except Exception as e:
        _log(f"任务异常: {e}")
        _app_state["last_result"] = {"success": False, "error": str(e)}
    finally:
        _app_state["running"] = False
        _app_state["current_task"] = None
    
    return _app_state["last_result"]

# ============ 路由 ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页仪表盘"""
    downloaded_ids = load_downloaded_ids()
    channel_data = load_channel_data()
    output_files = get_output_files()
    
    # 统计（跳过 NA 或空值）
    def _is_short(v):
        ds = v.get("duration_sec", "")
        try:
            return float(ds) < 180
        except (ValueError, TypeError):
            return False
    short_videos = [v for v in channel_data if _is_short(v)]
    
    stats = {
        "total_videos": len(channel_data),
        "downloaded": len(downloaded_ids),
        "pending": len(channel_data) - len(downloaded_ids),
        "output_files": len(output_files),
        "short_videos": len(short_videos),
    }
    
    return HTMLResponse(_render("index.html", {
        "version": VERSION,
        "stats": stats,
        "state": _app_state,
        "config": {
            "channel_url": YTWEB,
            "max_downloads": MAX_DOWNLOADS_PER_RUN,
            "interval_hours": SLEEP_INTERVAL // 3600,
        }
    }))

@app.get("/videos", response_class=HTMLResponse)
async def videos_page(request: Request, filter: str = "all"):
    """视频列表页"""
    downloaded_ids = load_downloaded_ids()
    channel_data = load_channel_data()
    
    videos = []
    for v in channel_data:
        vid = v["id"]
        is_downloaded = vid in downloaded_ids
        try:
            duration_sec = float(v.get("duration_sec", 0)) if v.get("duration_sec") else 0
        except (ValueError, TypeError):
            duration_sec = 0
        
        if filter == "downloaded" and not is_downloaded:
            continue
        if filter == "pending" and is_downloaded:
            continue
        if filter == "short" and duration_sec >= 180:
            continue
            
        videos.append({
            **v,
            "downloaded": is_downloaded,
            "is_short": duration_sec < 180,
        })
    
    return HTMLResponse(_render("videos.html", {
        "videos": videos[:200],
        "filter": filter,
        "total": len(channel_data),
    }))

@app.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    """文件浏览页"""
    files = get_output_files()
    categories = sorted(set(f["category"] for f in files))
    total_size = round(sum(f["size_mb"] for f in files), 2)
    return HTMLResponse(_render("files.html", {
        "files": files,
        "categories": categories,
        "total_size": total_size,
    }))

@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """日志页"""
    return HTMLResponse(_render("logs.html", {
        "logs": _app_state["logs"],
    }))

@app.get("/api/logs")
async def api_logs():
    """API: 获取日志"""
    return {"logs": _app_state["logs"], "running": _app_state["running"]}

@app.post("/api/download")
async def api_download(video_id: str = Form(...)):
    """API: 手动下载视频"""
    if _app_state["running"]:
        raise HTTPException(400, "已有任务在运行")
    
    # 启动后台任务
    asyncio.create_task(run_download_task(video_id))
    return {"success": True, "message": f"开始下载 {video_id}"}

@app.post("/api/scan")
async def api_scan():
    """API: 扫描频道"""
    if _app_state["running"]:
        raise HTTPException(400, "已有任务在运行")
    
    asyncio.create_task(run_download_task(None))
    return {"success": True, "message": "开始频道扫描"}

@app.get("/api/status")
async def api_status():
    """API: 获取状态"""
    return {
        "running": _app_state["running"],
        "current_task": _app_state["current_task"],
        "last_run": _app_state["last_run"],
        "last_result": _app_state["last_result"],
    }

@app.get("/download/{filepath:path}")
async def download_file(filepath: str):
    """下载 output 中的文件"""
    full_path = os.path.join(DST_PATH, filepath)
    if not os.path.exists(full_path) or not full_path.startswith(DST_PATH):
        raise HTTPException(404, "文件不存在")
    return FileResponse(full_path, filename=os.path.basename(filepath))

# ============ 主进程：Web + 定时调度 ============

def _scheduler_loop():
    """后台定时调度循环（运行在主线程同一进程）"""
    import time as _time
    _log(f"调度器启动，定时间隔 {SLEEP_INTERVAL}s ({SLEEP_INTERVAL // 3600}h)")
    _run_count = 0
    
    while True:
        _run_count += 1
        _log(f"=== 第 {_run_count} 次执行 ===")
        
        try:
            os.makedirs(DOWNLOAD_PATH, exist_ok=True)
            run_logger = RunLogger()
            
            # 1. 获取频道列表
            _log("正在获取频道列表...")
            playlist = get_playlist_info(YTWEB, run_logger)
            if not playlist:
                _log("获取频道列表失败，跳过")
                _time.sleep(SLEEP_INTERVAL)
                continue
            
            # 2. 加载历史 + 对比
            prev_map = {}
            if os.path.exists(CHANNEL_IDS_FILE):
                with open(CHANNEL_IDS_FILE, 'r', encoding='utf-8') as f:
                    next(f, None)
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) >= 5 and parts[0]:
                            prev_map[parts[0]] = parts[1]
            
            new_map = {v["id"]: v for v in playlist}
            new_ids = set(new_map.keys()) - set(prev_map.keys())
            
            if new_ids:
                _log(f"发现 {len(new_ids)} 个新视频")
            else:
                _log("没有新视频")
            
            # 3. 保存快照
            with open(CHANNEL_IDS_FILE, 'w', encoding='utf-8') as f:
                f.write("id,title,upload_date,duration_fmt,duration_sec\n")
                for v in playlist:
                    from utils import format_duration as _fd
                    dur = _fd(v["duration"])
                    title = v["title"].replace('"', '""')
                    f.write(f'{v["id"]},"{title}",{v["upload_date"]},{dur},{v["duration"]}\n')
            
            # 4. 增量下载
            if os.path.exists(ID_LOG_FILE):
                with open(ID_LOG_FILE, 'r', encoding='utf-8') as f:
                    downloaded_ids = set(line.strip() for line in f if line.strip())
            else:
                downloaded_ids = set()
            
            download_count = 0
            for v in playlist:
                if download_count >= MAX_DOWNLOADS_PER_RUN:
                    _log(f"达到下载限制 {MAX_DOWNLOADS_PER_RUN}，停止")
                    break
                
                vid = v["id"]
                if vid in downloaded_ids:
                    continue
                
                _log(f"开始下载: {vid} | {v['title'][:50]}")
                rc, filepath, size_mb = download_video(vid, DOWNLOAD_PATH, run_logger)
                
                if rc == 0:
                    downloaded_ids.add(vid)
                    with open(ID_LOG_FILE, 'w', encoding='utf-8') as idf:
                        idf.write('\n'.join(downloaded_ids))
                    
                    fname = os.path.basename(filepath)
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    from logger import write_csv_row as _wcr
                    _wcr(LOG_FILE, f'{ts},{vid},"{v["title"][:60]}",{v["upload_date"]},{_fd(v["duration"])},{size_mb:.2f},{fname}')
                    
                    # 重命名 + 移动
                    chagname(DOWNLOAD_PATH, run_logger)
                    move_files(DOWNLOAD_PATH, DST_PATH, channel_file=CHANNEL_IDS_FILE)
                    download_count += 1
                    _app_state["last_result"] = {"success": True, "video_id": vid, "size_mb": size_mb}
                else:
                    _log(f"下载失败: {vid}")
                    _app_state["last_result"] = {"success": False, "video_id": vid, "error": "下载失败"}
            
            _log("本次执行完成")
            
        except Exception as e:
            _log(f"执行异常: {e}")
        
        _app_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if SLEEP_INTERVAL <= 0:
            _log("SLEEP_INTERVAL=0，单次运行模式，退出")
            break
        
        next_time = datetime.fromtimestamp(time.time() + SLEEP_INTERVAL).strftime("%H:%M:%S")
        _log(f"下次执行: {next_time} ({SLEEP_INTERVAL}s 后)")
        _time.sleep(SLEEP_INTERVAL)


if __name__ == "__main__":
    import threading
    import uvicorn
    
    # 启动调度线程
    scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    scheduler_thread.start()
    
    # 主线程跑 Web 服务
    _log("Web 服务启动，监听 0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
