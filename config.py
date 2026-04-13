"""
BabyBus 下载器 — 配置模块
路径、URL、超参等统一在此管理
"""

import os
import platform

VERSION = "0.5"

# ===== subprocess 编码（Windows=GBK, Linux=UTF-8） =====
SUBPROCESS_ENCODING = 'gbk' if platform.system() == 'Windows' else 'utf-8'

# ===== 定时间隔（秒），0=只跑一次 =====
SLEEP_INTERVAL = int(os.environ.get('SLEEP_INTERVAL', '21600'))  # 默认6小时

# ===== 项目根目录（始终相对于脚本自身位置） =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# ===== 配置（支持环境变量覆盖，Docker/多平台通用） =====
YTWEB = os.environ.get('YTWEB', 'https://www.youtube.com/@BabyBusTC/videos')
DOWNLOAD_PATH = os.environ.get('DOWNLOAD_PATH',
    '/downloads' if os.environ.get('DOCKER') else
    (os.path.join(BASE_DIR, 'temp_dl') if platform.system() == 'Windows' else '/tmp/downloads'))
DST_PATH = os.environ.get('DST_PATH',
    '/output' if os.environ.get('DOCKER') else
    (os.path.join(BASE_DIR, 'downloads') if platform.system() == 'Windows' else '/tmp/output'))

LOG_FILE = os.path.join(LOGS_DIR, 'logs.csv')
ID_LOG_FILE = os.path.join(LOGS_DIR, 'id_download_log.csv')
CHANNEL_IDS_FILE = os.path.join(LOGS_DIR, 'channel_ids_latest.txt')

# 每次运行最多下载视频数
MAX_DOWNLOADS_PER_RUN = 3
