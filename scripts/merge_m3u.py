#!/usr/bin/env python3
"""合并虎牙和斗鱼直播源为M3U播放列表"""
import json
import os
from datetime import datetime

HUYA_FILE = "/tmp/iptv_update/huya.json"
DOUYU_FILE = "/tmp/iptv_update/douyu.json"
OUTPUT_FILE = "/tmp/iptv_update/huya_douyu_movie.m3u"

os.makedirs("/tmp/iptv_update", exist_ok=True)

lines = []
lines.append('#EXTM3U')
lines.append('# 虎牙+斗鱼 影视轮播直播源')
lines.append(f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
lines.append('# 来源: 虎牙一起看分类 & 斗鱼一起看分类')
lines.append('# 自动更新脚本: https://github.com/snaktoo/iptv-huya-douyu')
lines.append('#')
lines.append('')

# === 1. 虎牙频道 (HLS) ===
lines.append('# ===== 虎牙直播 - 影视轮播 =====')
lines.append('# 格式: HLS (m3u8)')
lines.append('')

huya_data = []
if os.path.exists(HUYA_FILE):
    with open(HUYA_FILE, 'r', encoding='utf-8') as f:
        huya_data = json.load(f)

for ch in huya_data:
    title = ch.get('title', 'Unknown')
    url = ch.get('url', '')
    nick = ch.get('nick', '')
    room_id = ch.get('room_id', '')
    
    if not url:
        continue
    
    # 清理标题
    safe_title = title.replace('\n', ' ').replace('\r', '').strip()
    if not safe_title or safe_title == 'Unknown':
        safe_title = nick
    
    # 去重 - 检查相同URL
    # 构建M3U条目
    tvg_name = safe_title
    lines.append(f'#EXTINF:-1 group-title="虎牙影视" tvg-name="{tvg_name}",{tvg_name}')
    lines.append(url)
    lines.append('')

# === 2. 斗鱼频道 (FLV) ===
lines.append('# ===== 斗鱼直播 - 影视轮播 =====')
lines.append('# 格式: FLV')
lines.append('')

douyu_data = []
if os.path.exists(DOUYU_FILE):
    with open(DOUYU_FILE, 'r', encoding='utf-8') as f:
        douyu_data = json.load(f)

for ch in douyu_data:
    title = ch.get('title', 'Unknown')
    url = ch.get('url', '')
    nick = ch.get('nick', '')
    quality = ch.get('quality', '')
    room_id = ch.get('room_id', '')
    
    if not url:
        continue
    
    safe_title = title.replace('\n', ' ').replace('\r', '').strip()
    if not safe_title or safe_title == 'Unknown':
        safe_title = nick
    
    display_title = f"{safe_title} ({quality})" if quality else safe_title
    
    lines.append(f'#EXTINF:-1 group-title="斗鱼影视" tvg-name="{display_title}",{display_title}')
    lines.append(url)
    lines.append('')

# 写入文件
content = '\n'.join(lines)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

huya_count = len(huya_data)
douyu_count = len(douyu_data)
total = huya_count + douyu_count

print(f"M3U: Generated {OUTPUT_FILE}")
print(f"  Huya: {huya_count} channels")
print(f"  Douyu: {douyu_count} channels")
print(f"  Total: {total} channels")
print(f"  Lines: {len(lines)}")