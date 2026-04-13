"""
BabyBus 下载器 — 日志模块
CSV 日志写入、运行日志收集
"""

import os

_LOG_HEADER = "time,id,title,upload_date,duration,size_mb,filename"


def write_csv_row(filepath, row):
    """写入一行 CSV，自动补 header"""
    needs_header = not os.path.exists(filepath)
    with open(filepath, 'a', encoding='utf-8') as f:
        if needs_header:
            f.write(_LOG_HEADER + "\n")
        f.write(row + "\n")


class RunLogger:
    """运行日志收集器，替代原来的全局 logs 列表"""

    def __init__(self):
        self.logs = []

    def log(self, msg):
        self.logs.append(msg)

    def clear(self):
        self.logs = []

    def __str__(self):
        return str(self.logs)
