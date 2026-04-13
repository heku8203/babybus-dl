# BabyBus 下载器 v0.5

批量下载 BabyBus YouTube 频道视频，自动重命名、智能分类整理，支持 Web UI 管理。

## 模块结构

| 文件 | 职责 |
|------|------|
| `main.py` | 主流程入口：频道对比 → 增量下载 → 重命名 → 分类移动，支持定时循环 |
| `config.py` | 配置中心：路径、URL、版本号、超参、编码适配 |
| `fetcher.py` | 频道列表获取：yt-dlp 拉取元数据 |
| `downloader.py` | 视频下载：单视频下载 + 文件校验 |
| `mover.py` | 文件整理：基于 channel_ids_latest 元数据智能分类 |
| `utils.py` | 工具函数：ffmpeg/node 查找、命令构建、时长格式化、emoji 清理 |
| `logger.py` | 日志模块：CSV 写入、运行日志收集 |
| `web.py` | FastAPI Web UI 服务（端口 8080），仪表盘/视频列表/文件管理/日志页面 |
| `web_templates.py` | HTML 模板（内嵌，无外部文件依赖） |
| `Dockerfile` | Docker 镜像构建 |
| `docker-compose.yml` | Docker Compose 配置 |

## 依赖

- Python 3.8+
- yt-dlp
- ffmpeg

## 本地使用

```bash
python main.py
```

## Docker 使用

### 构建 & 运行

```bash
docker compose up -d
```

### 查看日志

```bash
docker compose logs -f
```

### 停止

```bash
docker compose down
```

### 导入镜像（未推送到 registry 时）

```bash
docker load -i babybus-dl-v0.5.tar
```

## 配置

编辑 `config.py` 或通过环境变量覆盖：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `DOCKER` | 未设置 | 设为 `1` 启用 Docker 路径模式 |
| `YTWEB` | `https://www.youtube.com/@BabyBusTC/videos` | 频道 URL |
| `DOWNLOAD_PATH` | `./temp_dl` (Win) / `/downloads` (Docker) | 临时下载目录 |
| `DST_PATH` | `./downloads` (Win) / `/output` (Docker) | 最终输出目录 |
| `SLEEP_INTERVAL` | `21600` (6小时) | 循环间隔秒数，0=只跑一次 |
| `MAX_DOWNLOADS_PER_RUN` | `3` | 每次最多下载数 |

## Docker 卷映射

| 容器路径 | 说明 |
|---------|------|
| `/app/logs` | 运行日志、频道快照、下载记录（持久化） |
| `/output` | 最终视频输出（按分类子目录） |

## 智能分类规则

`mover.py` 基于 `channel_ids_latest.txt` 元数据做智能分类：

| 分类 | 匹配关键词 |
|------|-----------|
| 安全警長啦咘啦哆｜水城季 | 水城季 |
| 安全警長啦咘啦哆｜守護季 | 守護季 |
| 安全警長啦咘啦哆 | 安全警長啦咘啦哆 |
| 奇妙救援隊 | 奇妙救援隊 |
| 美食家族 | 美食 |
| 奇妙漢字 | 漢字/汉字 |
| 尼歐歐歐 | 尼歐歐歐/想象大爆發 |
| 奇奇妙妙 | 奇奇/妙妙 |
| 恐龍兒歌 | 恐龍 |
| 交通工具 | 車車/汽车/交通工具 |
| 儿歌童谣 | 兒歌/儿歌/童謠/Kids Song |
| 动画 | 卡通片/動畫/Cartoon |
| 安全教育 | 安全 |
| 节日特辑｜春节 | 新春/新年/春节 |
| 节日特辑｜圣诞 | 圣诞 |
| 其他 | 未匹配 |

## 目录结构

```
BabyBus下载器/
├── config.py
├── fetcher.py
├── downloader.py
├── mover.py
├── utils.py
├── logger.py
├── main.py
├── web.py
├── web_templates.py
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── README.md
├── logs/                    # 运行日志
│   ├── logs.csv
│   ├── id_download_log.csv
│   └── channel_ids_latest.txt
└── output/                  # Docker 输出目录（映射到本地 downloads/）
```

> 本地开发时视频存放在 `downloads/` 目录，Docker 模式下存放在 `output/` 目录。

## 更新日志

### v0.5 (2026-04-13)
- 新增 Web UI（FastAPI）：仪表盘 / 视频列表 / 文件管理 / 实时日志
- 模板内嵌到 web_templates.py，移除外部文件依赖
- 修复 starlette 1.0.0 与 Jinja2Templates 兼容性 bug
- 修复 duration_sec 浮点数字符串（如 `"1365.0"`）和 `"NA"` 值的处理
- Dockerfile 优化：减少构建层，Python 3.13 slim

### v0.4 (2026-04-13)
- Docker 全流程测试通过，镜像导出为 250MB tar 包
- 国内清华 pip/apt 镜像，构建时间从 10 分钟缩短至 ~80 秒
- 添加 `PYTHONUNBUFFERED=1` 解决 docker logs 无输出问题
- 修复 Docker Desktop Windows 端口映射问题（bridge 模式 + 8080:8080）

### v0.3 (2026-04-13)
- 修复 Docker 内 yt-dlp 找不到 JavaScript 运行时（写入 yt-dlp config）
- 修复跨设备移动文件报错（`os.rename` → `shutil.move`）
- 新增 `--video ID` 单视频下载模式
- Docker 使用 `network_mode: host` 避免地区限制

### v0.2 (2026-04-13)
- 智能分类：基于 channel_ids_latest 元数据，识别系列/季/角色
- 新增分类：水城季、守護季、尼歐歐歐、恐龍兒歌、节日特辑等
- Docker Compose 支持
- 优化 mover.py 分类优先级

### v0.1 (2026-04-13)
- 从单文件重构为模块化架构
- 修复 Windows GBK 编码导致 yt-dlp 中文输出乱码
- 修复 chagname 子目录文件重命名错位 bug
- 文件名清理：去 emoji、品牌词、视频 ID、合并连续竖线
- Docker 支持：Dockerfile + 定时循环 + 优雅退出
- subprocess 编码自适应（Windows=GBK, Linux=UTF-8）
