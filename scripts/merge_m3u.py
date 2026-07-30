#!/usr/bin/env python3
"""合并虎牙、斗鱼、央视直播源为统一M3U播放列表"""
import json
import os
from datetime import datetime

HUYA_FILE = "/tmp/iptv_update/huya.json"
DOUYU_FILE = "/tmp/iptv_update/douyu.json"
OUTPUT_FILE = "/tmp/iptv_update/huya_douyu_movie.m3u"
FINAL_FILE = "/sdcard/Download/huya_douyu_movie.m3u"

os.makedirs("/tmp/iptv_update", exist_ok=True)

# ===== 央视总台17个官方频道（静态，央视网官方CDN） =====
CCTV_CHANNELS = [
    ("CCTV-1 综合", "CCTV1", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv1_1/index.m3u8?b=200-2100"),
    ("CCTV-2 财经", "CCTV2", "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv2_1/index.m3u8?b=200-2100"),
    ("CCTV-3 综艺", "CCTV3", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv3_1/index.m3u8?b=200-2100"),
    ("CCTV-4 中文国际（亚）", "CCTV4", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv4_1/index.m3u8?b=200-2100"),
    ("CCTV-5 体育", "CCTV5", "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv5_1/index.m3u8?b=200-2100"),
    ("CCTV-5+ 体育赛事", "CCTV5+", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv5plus_1/index.m3u8?b=200-2100"),
    ("CCTV-6 电影", "CCTV6", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv6_1/index.m3u8?b=200-2100"),
    ("CCTV-7 国防军事", "CCTV7", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv7_1/index.m3u8?b=200-2100"),
    ("CCTV-8 电视剧", "CCTV8", "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv8_1/index.m3u8?b=200-2100"),
    ("CCTV-9 纪录", "CCTV9", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctvjilu_1/index.m3u8?b=200-2100"),
    ("CCTV-10 科教", "CCTV10", "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv10_1/index.m3u8?b=200-2100"),
    ("CCTV-11 戏曲", "CCTV11", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv11_1/index.m3u8?b=200-2100"),
    ("CCTV-12 社会与法", "CCTV12", "https://ldocctvwbcdbd.a.bdydns.com/ldocctvwbcd/cdrmldcctv12_1/index.m3u8?b=200-2100"),
    ("CCTV-13 新闻", "CCTV13", "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv13_1/index.m3u8?b=200-2100"),
    ("CCTV-14 少儿", "CCTV14", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctvchild_1/index.m3u8?b=200-2100"),
    ("CCTV-15 音乐", "CCTV15", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv15_1/index.m3u8?b=200-2100"),
    ("CCTV-16 奥林匹克", "CCTV16", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv16_1/index.m3u8?b=200-2100"),
    ("CCTV-17 农业农村", "CCTV17", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv17_1/index.m3u8?b=200-2100"),
]

lines = []
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
lines.append('#EXTM3U')
lines.append(f'# 综合IPTV直播源 (央视 + 虎牙1080P + 斗鱼1080P)')
lines.append(f'# 生成时间: {now_str}')
lines.append('# 来源: 央视网 tv.cctv.com/live | 虎牙一起看分类 | 斗鱼一起看分类')
lines.append('# 清晰度: 央视720p / 虎牙1080P蓝光 / 斗鱼1080P原画')
lines.append('# 自动更新: GitHub Actions 每30分钟')
lines.append('')

# ===== 一、央视总台 =====
lines.append('# ===== 央视总台官方频道（720p） =====')
lines.append('')
for name, tvg_id, url in CCTV_CHANNELS:
    lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="央视",{name}')
    lines.append(url)

# ===== 二、虎牙1080P =====
lines.append('')
lines.append('# ===== 虎牙直播 - 1080P影视轮播 =====')
lines.append('')
huya_data = []
if os.path.exists(HUYA_FILE):
    with open(HUYA_FILE, 'r', encoding='utf-8') as f:
        huya_data = json.load(f)
for ch in huya_data:
    title = ch.get('title', 'Unknown')
    url = ch.get('url', '')
    quality = ch.get('quality', '')
    if not url:
        continue
    safe_title = title.replace('\\n', ' ').replace('\\r', '').strip()[:40]
    if not safe_title or safe_title == 'Unknown':
        safe_title = ch.get('nick', 'Huya')[:30]
    display = f"{safe_title} [{quality}]" if quality else safe_title
    lines.append(f'#EXTINF:-1 group-title="虎牙影视(1080P)" tvg-name="{display}",{display}')
    lines.append(url)

# ===== 三、斗鱼1080P =====
lines.append('')
lines.append('# ===== 斗鱼直播 - 1080P影视轮播 =====')
lines.append('')
douyu_data = []
if os.path.exists(DOUYU_FILE):
    with open(DOUYU_FILE, 'r', encoding='utf-8') as f:
        douyu_data = json.load(f)
for ch in douyu_data:
    title = ch.get('title', 'Unknown')
    url = ch.get('url', '')
    quality = ch.get('quality', '')
    if not url:
        continue
    safe_title = title.replace('\\n', ' ').replace('\\r', '').strip()[:40]
    if not safe_title or safe_title == 'Unknown':
        safe_title = ch.get('nick', 'Douyu')[:30]
    display = f"{safe_title} [{quality}]" if quality else safe_title
    lines.append(f'#EXTINF:-1 group-title="斗鱼影视(1080P)" tvg-name="{display}",{display}')
    lines.append(url)

content = '\n'.join(lines)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

import shutil
os.makedirs(os.path.dirname(FINAL_FILE), exist_ok=True)
if os.path.exists(FINAL_FILE):
    os.remove(FINAL_FILE)
shutil.copy2(OUTPUT_FILE, FINAL_FILE)

cctv_count = len(CCTV_CHANNELS)
huya_count = len(huya_data)
douyu_count = len(douyu_data)
total = cctv_count + huya_count + douyu_count
print(f"M3U: Generated {OUTPUT_FILE}")
print(f"  CCTV: {cctv_count} channels")
print(f"  Huya: {huya_count} channels (1080P)")
print(f"  Douyu: {douyu_count} channels (1080P)")
print(f"  Total: {total} channels")
print(f"  Saved to: {FINAL_FILE}")
