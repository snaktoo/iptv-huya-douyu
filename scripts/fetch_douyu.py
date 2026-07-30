#!/usr/bin/env python3
"""抓取斗鱼一起看分类下所有影视直播间的流地址（并发版 + 增量保存）"""
import subprocess
import json
import requests
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
import signal

OUTPUT_FILE = "/tmp/iptv_update/douyu.json"
os.makedirs("/tmp/iptv_update", exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.douyu.com/'
}

# === 1. 获取斗鱼房间列表 ===
all_rooms = []
page = 1
while True:
    try:
        url = f'https://www.douyu.com/gapi/rkc/directory/mixList/2_208/{page}'
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        if not data.get('data') or not data['data'].get('rl'):
            break
        rooms = data['data']['rl']
        if not rooms:
            break
        all_rooms.extend(rooms)
        if len(rooms) < 20:
            break
        page += 1
    except Exception as e:
        print(f"Douyu list API error: {e}", file=sys.stderr)
        break

print(f"Douyu: Found {len(all_rooms)} rooms total", flush=True)

# === 2. 过滤出影视相关房间 ===
def is_movie_room(room_name, nickname):
    name = (room_name + ' ' + nickname).lower()
    movie_kw = ['电影', '电视', '剧', '影视', '综艺', '动漫', '音乐', 'mv',
                '女团', '纪录片', '搞笑', '经典', '功夫', '港片', '周星驰',
                '喜剧', '恐怖', '动作', '爱情', '科幻', '国漫', '动漫',
                'kpop', '追剧', '影院', '娱乐', '小品', '怀旧', '解说']
    skip_kw = ['游戏', 'lol', '英雄联盟', '王者荣耀', '吃鸡', '绝地求生',
               '永劫', '原神', 'cf', 'csgo', 'dota', '炉石', 'lpl', 'kpl',
               '赛事', '陪玩', '代练']
    has_skip = any(kw in name for kw in skip_kw)
    has_movie = any(kw in name for kw in movie_kw)
    return has_movie and not has_skip

movie_rooms = [r for r in all_rooms if is_movie_room(r.get('rn','') or '', r.get('nn','') or '')]
print(f"Douyu: {len(movie_rooms)} are movie-related", flush=True)
# Top30 by online count
movie_rooms.sort(key=lambda r: r.get("ol",0) or 0, reverse=True)
movie_rooms = movie_rooms[:30]
print(f"Douyu: Top 30 hottest movie rooms selected", flush=True)


if not movie_rooms:
    # 保存空结果并退出
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)
    print("Douyu: No movie rooms found, exiting", flush=True)
    sys.exit(0)

# === 3. 并发获取流地址 ===
results = []
results_lock = None  # not needed, CPython GIL protects list append

def get_douyu_stream(room_info):
    room_id = str(room_info.get('rid', ''))
    room_name = room_info.get('rn', '') or ''
    nickname = room_info.get('nn', '') or ''
    if not room_id:
        return None
    try:
        result = subprocess.run(
            ['ykdl', '--info', '--json', f'https://www.douyu.com/{room_id}'],
            capture_output=True, text=True, timeout=20
        )
        output = result.stdout.strip()
        if not output:
            return None
        info = json.loads(output)
        streams = info.get('streams', {})
        if not streams:
            return None

        def quality_score(profile):
            p = profile.lower()
            if '1080' in p and '60' in p: return 0
            if '1080' in p and '30' in p: return 1
            if '1080' in p: return 2
            if '4k' in p or '超清' in p: return 3
            if '720' in p and '60' in p: return 4
            if '720' in p and '30' in p: return 5
            if '720' in p: return 6
            if '高清' in p: return 7
            if '原画' in p: return 8
            return 9

        best_key = min(streams.keys(),
                       key=lambda k: quality_score(streams[k].get('profile','') or streams[k].get('video_profile','')))
        best_stream = streams[best_key]
        src_list = best_stream.get('src', [])
        if not src_list:
            return None
        stream_url = src_list[0]
        profile = best_stream.get('profile', '') or best_stream.get('video_profile', '') or ''

        quality_tag = profile
        if '1080' in profile and '60' in profile: quality_tag = '1080P60'
        elif '1080' in profile and '30' in profile: quality_tag = '1080P30'
        elif '1080' in profile: quality_tag = '1080P'
        elif '720' in profile and '60' in profile: quality_tag = '720P60'
        elif '720' in profile and '30' in profile: quality_tag = '720P30'
        elif '720' in profile: quality_tag = '720P'
        elif '超清' in profile: quality_tag = '超清'
        elif '高清' in profile: quality_tag = '高清'
        elif '原画' in profile: quality_tag = '原画'

        return {"title": room_name, "nick": nickname, "url": stream_url,
                "room_id": room_id, "quality": quality_tag}
    except subprocess.TimeoutExpired:
        pass
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"  Error {room_id}: {e}", file=sys.stderr)
    return None

completed = 0
total = len(movie_rooms)
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(get_douyu_stream, room): room for room in movie_rooms}
    for future in as_completed(futures):
        result = future.result()
        completed += 1
        if result:
            results.append(result)
            print(f"  ✓ [{completed}/{total}] {result['title'][:30]:30s} [{result['quality']}]", flush=True)
        else:
            if completed % 10 == 0:
                print(f"  ... {completed}/{total} processed", flush=True)

# 最终保存
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Douyu: Got {len(results)} valid streams, saved to {OUTPUT_FILE}", flush=True)