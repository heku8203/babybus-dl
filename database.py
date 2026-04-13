"""
BabyBus 下载器 — SQLite 数据库模块
替代 CSV 日志：logs.csv / id_download_log.csv / channel_ids_latest.txt
"""

import os
import sqlite3
import threading
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

from config import LOGS_DIR, DB_PATH

# ===== Schema =====

_SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id          TEXT PRIMARY KEY,      -- YouTube video ID
    title       TEXT,
    upload_date  TEXT,                  -- YYYYMMDD
    duration_fmt TEXT,                  -- "2:30" 格式
    duration_sec REAL,                 -- 秒数，秒级精度
    category    TEXT,                  -- 分类（见 mover.py）
    added_at    TEXT                   -- 首次加入频道快照的时间
);

CREATE TABLE IF NOT EXISTS downloads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL,
    title       TEXT,
    upload_date TEXT,
    duration    TEXT,
    size_mb     REAL,
    filename    TEXT,
    status      TEXT DEFAULT 'ok',     -- ok / failed
    downloaded_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT,
    ended_at    TEXT,
    new_videos  INTEGER DEFAULT 0,
    downloaded  INTEGER DEFAULT 0,
    failed      INTEGER DEFAULT 0,
    result      TEXT                   -- JSON 摘要
);

CREATE TABLE IF NOT EXISTS app_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT,
    level       TEXT DEFAULT 'info',
    message     TEXT
);

CREATE INDEX IF NOT EXISTS idx_videos_upload ON videos(upload_date);
CREATE INDEX IF NOT EXISTS idx_downloads_video ON downloads(video_id);
CREATE INDEX IF NOT EXISTS idx_downloads_at   ON downloads(downloaded_at);
"""

# ===== 单例连接 =====

_lock = threading.Lock()
_local = threading.local()

def _db() -> sqlite3.Connection:
    """获取当前线程的 db 连接（线程安全）"""
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys = ON")
    return _local.conn

def _init_db():
    """初始化表结构（幂等）"""
    with _lock:
        db = _db()
        db.executescript(_SCHEMA)
        db.commit()

# ===== 工具 =====

def is_downloaded(video_id: str) -> bool:
    """检查视频是否已下载"""
    db = _db()
    cur = db.execute("SELECT 1 FROM downloads WHERE video_id=? AND status='ok' LIMIT 1", (video_id,))
    return cur.fetchone() is not None

def get_downloaded_ids() -> set:
    """返回所有已下载 video_id 集合"""
    db = _db()
    cur = db.execute("SELECT video_id FROM downloads WHERE status='ok'")
    return {row[0] for row in cur.fetchall()}

# ===== videos 表 =====

def upsert_video(video_id: str, title: str, upload_date: str,
                 duration_fmt: str, duration_sec: float, category: str = ""):
    """插入或更新频道视频（首次出现在快照时调用）"""
    db = _db()
    db.execute("""
        INSERT INTO videos (id, title, upload_date, duration_fmt, duration_sec, category, added_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            upload_date=excluded.upload_date,
            duration_fmt=excluded.duration_fmt,
            duration_sec=excluded.duration_sec,
            category=excluded.category
    """, (video_id, title, upload_date, duration_fmt, duration_sec, category,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()

def update_video_category(video_id: str, category: str):
    """下载后更新分类"""
    db = _db()
    db.execute("UPDATE videos SET category=? WHERE id=?", (category, video_id))
    db.commit()

def get_all_videos() -> list:
    """返回所有频道视频（用于 Web UI 列表）"""
    db = _db()
    cur = db.execute("""
        SELECT v.id, v.title, v.upload_date, v.duration_fmt, v.duration_sec,
               v.category,
               (SELECT 1 FROM downloads d WHERE d.video_id=v.id AND d.status='ok' LIMIT 1) AS downloaded
        FROM videos v ORDER BY v.upload_date DESC
    """)
    cols = ["id", "title", "upload_date", "duration_fmt", "duration_sec", "category", "downloaded"]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def get_pending_videos(limit: int = 10) -> list:
    """返回未下载的新视频（用于下载队列）"""
    db = _db()
    cur = db.execute("""
        SELECT v.id, v.title, v.upload_date, v.duration_fmt, v.duration_sec
        FROM videos v
        WHERE NOT EXISTS (SELECT 1 FROM downloads d WHERE d.video_id=v.id AND d.status='ok')
        ORDER BY v.upload_date DESC
        LIMIT ?
    """, (limit,))
    cols = ["id", "title", "upload_date", "duration_fmt", "duration_sec"]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

# ===== downloads 表 =====

def log_download(video_id: str, title: str, upload_date: str,
                  duration: str, size_mb: float, filename: str,
                  status: str = "ok"):
    """记录一次下载（成功或失败）"""
    db = _db()
    db.execute("""
        INSERT INTO downloads (video_id, title, upload_date, duration, size_mb, filename, status, downloaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (video_id, title, upload_date, duration, size_mb, filename, status,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()

# ===== runs 表 =====

def start_run() -> int:
    """开启一次运行，返回 run_id"""
    db = _db()
    cur = db.execute("INSERT INTO runs (started_at) VALUES (?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    db.commit()
    return cur.lastrowid

def end_run(run_id: int, new_videos: int, downloaded: int, failed: int, result: str = ""):
    """结束运行，更新统计"""
    db = _db()
    db.execute("""
        UPDATE runs SET ended_at=?, new_videos=?, downloaded=?, failed=?, result=?
        WHERE id=?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          new_videos, downloaded, failed, result, run_id))
    db.commit()

# ===== app_log 表 =====

def app_log(message: str, level: str = "info"):
    """应用级日志（轻量，随时可查）"""
    db = _db()
    db.execute("INSERT INTO app_log (ts, level, message) VALUES (?, ?, ?)",
               (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, message))
    db.commit()

def get_recent_logs(limit: int = 500) -> list:
    """获取最近的 app_log（用于 Web 日志页）"""
    db = _db()
    cur = db.execute("SELECT ts, message FROM app_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    return [f"[{r[0][-8:]}] {r[1]}" for r in reversed(rows)]

def get_download_history(limit: int = 100) -> list:
    """下载历史（用于 Web 视频列表，支持分页）"""
    db = _db()
    cur = db.execute("""
        SELECT video_id, title, upload_date, duration, size_mb, filename, status, downloaded_at
        FROM downloads ORDER BY id DESC LIMIT ?
    """, (limit,))
    cols = ["video_id", "title", "upload_date", "duration", "size_mb", "filename", "status", "downloaded_at"]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def get_stats() -> dict:
    """仪表盘统计数据"""
    db = _db()
    cur = db.execute("SELECT COUNT(*) FROM videos")
    total = cur.fetchone()[0] or 0
    cur = db.execute("SELECT COUNT(DISTINCT video_id) FROM downloads WHERE status='ok'")
    downloaded = cur.fetchone()[0] or 0
    cur = db.execute("SELECT COUNT(*) FROM downloads")
    total_dl = cur.fetchone()[0] or 0
    return {
        "total_videos": total,
        "downloaded": downloaded,
        "pending": max(0, total - downloaded),
        "total_downloads": total_dl,
    }

# ===== 迁移：CSV → SQLite =====

def migrate_from_csv():
    """一次性迁移：将已有 CSV 数据导入 SQLite（幂等）"""
    import re
    from config import LOG_FILE, ID_LOG_FILE, CHANNEL_IDS_FILE

    # 1. 迁移下载历史 logs.csv
    # 格式: timestamp, video_id, title, upload_date, duration, size_mb, filename
    # 用正则识别正确的 CSV 行，跳过 Python list 格式的旧日志
    _yt_id_pat = re.compile(r'^[a-zA-Z0-9_-]{10,12}$')
    _csv_row_pat = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},[a-zA-Z0-9_-]+,')
    if os.path.exists(LOG_FILE):
        migrated = 0
        db = _db()
        db.execute("DELETE FROM downloads")
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('time,id,title') or line.startswith('['):
                    continue  # 跳过 header 和 Python list 旧日志
                if not _csv_row_pat.match(line):
                    continue  # 不是标准 CSV 行
                # 用逗号分割，title 可能含逗号，用最后一次分割保证 video_id 在第一列
                parts = line.split(',')
                if len(parts) < 7 or not _yt_id_pat.match(parts[1].strip('"')):
                    continue
                ts, vid = parts[0], parts[1].strip('"')
                title = parts[2].strip('"')
                udate, dur = parts[3], parts[4]
                try:
                    size_mb = float(parts[5])
                except ValueError:
                    size_mb = 0.0
                fname = parts[6]
                db.execute("""
                    INSERT OR IGNORE INTO downloads
                    (video_id, title, upload_date, duration, size_mb, filename, status, downloaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'ok', ?)
                """, (vid, title, udate, dur, size_mb, fname, ts))
                migrated += 1
        if migrated:
            _db().commit()
            print(f"[DB 迁移] logs.csv: {migrated} 条下载记录已导入")

    # 2. 迁移频道快照 channel_ids_latest.txt
    if os.path.exists(CHANNEL_IDS_FILE):
        imported = 0
        with open(CHANNEL_IDS_FILE, 'r', encoding='utf-8') as f:
            next(f, None)  # skip header
            for line in f:
                parts = line.strip().split(',', 4)
                if len(parts) >= 5 and parts[0]:
                    vid, title, udate, dur_fmt, dur_sec = parts
                    title = title.strip('"')
                    try:
                        dur_sec = float(dur_sec)
                    except ValueError:
                        dur_sec = 0.0
                    upsert_video(vid, title, udate, dur_fmt, dur_sec)
                    imported += 1
        if imported:
            print(f"[DB 迁移] channel_ids_latest.txt: {imported} 条视频已导入")

    # 3. id_download_log.csv 已被 downloads 表覆盖，无需单独迁移
    if os.path.exists(ID_LOG_FILE):
        print("[DB 迁移] id_download_log.csv 已废弃，内容由 downloads 表提供")


# ===== 初始化 =====

_init_db()
