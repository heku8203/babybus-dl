"""
BabyBus 下载器 — 文件整理模块
重命名、分类、移动（基于 channel_ids_latest 元数据智能分类）
"""

import os
import re
import csv
import shutil
from utils import remove_emoji

# 分类规则（优先级从高到低）
CATEGORY_RULES = [
    # 系列/季
    (r'水城季', '安全警長啦咘啦哆｜水城季'),
    (r'守護季', '安全警長啦咘啦哆｜守護季'),
    (r'安全警長啦咘啦哆', '安全警長啦咘啦哆'),
    (r'奇妙救援隊', '奇妙救援隊'),
    (r'美食', '美食家族'),
    (r'漢字|汉字', '奇妙漢字'),
    
    # 角色/主题
    (r'尼歐歐歐|想象大爆發', '尼歐歐歐'),
    (r'奇奇|妙妙', '奇奇妙妙'),
    (r'恐龍', '恐龍兒歌'),
    (r'車車|汽车|交通工具', '交通工具'),
    (r'小猪佩奇', '小猪佩奇'),
    
    # 内容类型
    (r'兒歌|儿歌|童謠|Kids Song', '儿歌童谣'),
    (r'卡通片|動畫|Cartoon', '动画'),
    (r'安全', '安全教育'),
    
    # 节日/特辑
    (r'新春|新年|春节', '节日特辑｜春节'),
    (r'圣诞', '节日特辑｜圣诞'),
]


def load_channel_metadata(channel_file):
    """加载频道元数据，返回 {video_id: title} """
    meta = {}
    if not os.path.exists(channel_file):
        return meta
    try:
        with open(channel_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vid = row.get('id', '').strip()
                title = row.get('title', '').strip()
                if vid and title:
                    meta[vid] = title
    except Exception as e:
        print(f"加载频道元数据失败: {e}")
    return meta


def extract_video_id(filename):
    """从文件名提取 video_id（yt-dlp 默认格式包含 id）"""
    # 尝试匹配常见的 video id 格式：11位字母数字下划线连字符
    match = re.search(r'[a-zA-Z0-9_-]{11}', filename)
    if match:
        return match.group(0)
    return None


def smart_category(filename, video_id=None, channel_meta=None):
    """
    智能分类：优先使用 channel_ids_latest 的完整标题，其次用文件名
    """
    # 1. 尝试用 video_id 查元数据获取完整标题
    title_to_check = filename
    if video_id and channel_meta and video_id in channel_meta:
        title_to_check = channel_meta[video_id]
    
    # 2. 按优先级匹配分类规则
    for pattern, cat_name in CATEGORY_RULES:
        if re.search(pattern, title_to_check):
            return cat_name
    
    return "其他"


def category(filename, video_id=None, channel_meta=None):
    """兼容旧接口，实际调用 smart_category"""
    return smart_category(filename, video_id, channel_meta)


def chagname(path, run_logger=None):
    """清理下载文件名：去 emoji、去品牌词、去括号内容等"""
    for root, dirs, files in os.walk(path):
        for f in files:
            ext = os.path.splitext(f)[-1]
            if ext not in ('.mp4', '.m4a', '.jpg', '.txt', '.srt', '.opus', '.webm', '.mkv'):
                continue
            newname = remove_emoji(f)
            newname = newname.replace("更多", '_').replace("BabyBus寶寶巴士", '').replace("KidsSong", '')
            newname = re.sub('\【.*?\】', '', newname)
            newname = re.sub('\★.*?\★', '', newname)
            newname = re.sub('\「.*?\」', '', newname)
            newname = re.sub(r'_[a-zA-Z].*?_', '', newname)
            newname = re.sub(r'\(.*?\)', '', newname)
            newname = re.sub(r'\[.*?\]', '', newname)
            newname = newname.replace('寶寶巴士', '').replace('宝宝巴士', '').replace('BabyBus', '').replace(
                '_卡通片', '').replace('+更多', '_').replace('_合集', '').replace('_片', '').replace(
                '片片', '').replace(' ', '').replace('_.', '.').replace('__', '_').replace('__', '_').replace('＋更多合集', '')
            # 清理连续竖线和首尾竖线
            newname = re.sub(r'｜{2,}', '｜', newname)
            newname = re.sub(r'^｜+|｜+(?=\.)|｜+$', '', newname)
            newname = newname.replace('douyin', '').replace('❤️ZinnZinn', '')
            srcname = os.path.join(root, f)
            dstname = os.path.join(root, newname)
            if srcname == dstname:
                continue
            print('新文件名:', newname)
            if run_logger:
                run_logger.log(newname)
            if not os.path.exists(dstname):
                try:
                    os.rename(srcname, dstname)
                except FileExistsError:
                    base, ext = os.path.splitext(newname)
                    for i in range(1, 100):
                        dstname2 = os.path.join(root, f"{base}_{i}{ext}")
                        if not os.path.exists(dstname2):
                            os.rename(srcname, dstname2)
                            break
            else:
                print(f"  目标文件已存在，跳过: {newname}")
    print("重命名完毕")
    if run_logger:
        run_logger.log("重命名完毕")


def move_files(path, dst, channel_file=None):
    """
    按分类将文件移动到目标目录
    - 使用 channel_ids_latest 元数据做智能分类
    - 重复文件放入回收目录
    """
    # 加载频道元数据
    channel_meta = load_channel_metadata(channel_file) if channel_file else {}
    if channel_meta:
        print(f"已加载频道元数据: {len(channel_meta)} 条")
    
    for root, dirs, files in os.walk(path):
        for f in files:
            ext = os.path.splitext(f)[-1]
            if ext not in ('.mp4', '.m4a', '.jpg', '.txt', '.srt', '.opus', '.webm', '.mkv'):
                continue
            
            # 提取 video_id 用于查元数据
            video_id = extract_video_id(f)
            
            # 智能分类
            folder_name = category(f, video_id, channel_meta)
            folder = os.path.join(dst, folder_name)
            
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            srcpath = os.path.join(root, f)
            dstpath = os.path.join(folder, f)
            
            if not os.path.exists(dstpath):
                shutil.move(srcpath, dstpath)
                print(f'移动到 [{folder_name}]: {f}')
            else:
                recycle = os.path.join(os.path.dirname(dst), '巴士回收', f)
                recycle_dir = os.path.dirname(recycle)
                if not os.path.exists(recycle_dir):
                    os.makedirs(recycle_dir)
                shutil.move(srcpath, recycle)
                print(f'文件已存在,回收: {recycle}')
