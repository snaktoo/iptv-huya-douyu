#!/usr/bin/env python3
"""斗鱼一起看分类 - 只取1080P流"""
import subprocess, json, requests, os, sys, re
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_FILE = "/tmp/iptv_update/douyu.json"
os.makedirs("/tmp/iptv_update", exist_ok=True)
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
           'Referer': 'https://www.douyu.com/'}

# 获取房间列表
all_rooms = []
for page in range(1, 20):
    try:
        r = requests.get(f'https://www.douyu.com/gapi/rkc/directory/mixList/2_208/{page}',
                        headers=headers, timeout=15)
        data = r.json()
        if not data.get('data') or not data['data'].get('rl'):
            break
        rooms = data['data']['rl']
        if not rooms:
            break
        all_rooms.extend(rooms)
        if len(rooms) < 20:
            break
    except Exception as e:
        print(f"Douyu list error: {e}", file=sys.stderr)
        break

print(f"Douyu: {len(all_rooms)} rooms total", flush=True)

# 过滤影视类
MOVIE_KW = ['电影','电视','剧','影视','综艺','动漫','音乐','mv','女团','纪录片','搞笑',
            '经典','功夫','港片','周星驰','喜剧','恐怖','动作','爱情','科幻','国漫',
            'kpop','追剧','影院','娱乐','小品','怀旧','解说']
SKIP_KW = ['游戏','lol','英雄联盟','王者荣耀','吃鸡','绝地求生','永劫','原神',
           'cf','csgo','dota','炉石','lpl','kpl','赛事','陪玩','代练']

def is_movie(rn, nn):
    name = (rn + ' ' + nn).lower()
    return any(k in name for k in MOVIE_KW) and not any(k in name for k in SKIP_KW)

movie_rooms = [r for r in all_rooms if is_movie(r.get('rn','') or '', r.get('nn','') or '')]
movie_rooms.sort(key=lambda r: r.get("ol",0) or 0, reverse=True)
movie_rooms = movie_rooms[:180]  # 增加到180个以补偿1080P过滤损失
print(f"Douyu: {len(movie_rooms)} movie rooms selected", flush=True)

if not movie_rooms:
    with open(OUTPUT_FILE, 'w') as f:
        json.dump([], f)
    sys.exit(0)

# 1080P ONLY格式优先级 — 严格拒绝低于1080P的流
def quality_score(profile):
    p = profile.lower()
    # 1080P及以上: 接受
    if '4k' in p or '8k' in p: return 0
    if '蓝光' in p: return 1       # 蓝光4M/蓝光8M等
    if '1080' in p and '60' in p: return 2
    if '1080' in p: return 3
    # 以下全部拒绝 (超清/720P/高清/原画720P/原画360P/流畅)
    return 100  # 拒绝

def get_stream(room_info):
    room_id = str(room_info.get('rid', ''))
    room_name = room_info.get('rn', '') or ''
    nickname = room_info.get('nn', '') or ''
    if not room_id:
        return None
    try:
        res = subprocess.run(
            ['ykdl', '--info', '--json', f'https://www.douyu.com/{room_id}'],
            capture_output=True, text=True, timeout=20
        )
        out = res.stdout.strip()
        if not out:
            return None
        info = json.loads(out)
        streams = info.get('streams', {})
        if not streams:
            return None
        best_key = min(streams.keys(),
                      key=lambda k: quality_score(streams[k].get('profile','') or streams[k].get('video_profile','') or k))
        best = streams[best_key]
        src = best.get('src', [])
        if not src:
            return None
        profile = best.get('profile', '') or best.get('video_profile', '') or best_key
        # 严格1080P ONLY: 拒绝任何低于1080P的流
        score = quality_score(profile)
        if score >= 100:
            print(f"  Skip {room_id}: {profile} (not 1080P)", flush=True)
            return None
        title = info.get('title', room_name).strip()
        title = re.sub(r'[\\/:*?"<>|\t\n]', '', title)[:50] if title else room_name[:30]
        return {"title": title, "nick": nickname, "url": src[0], "room_id": room_id, "quality": profile}
    except Exception as e:
        print(f"  Err {room_id}: {e}", file=sys.stderr)
    return None

results = []
total = len(movie_rooms)
with ThreadPoolExecutor(max_workers=10) as ex:
    fut = {ex.submit(get_stream, rm): rm for rm in movie_rooms}
    for f in as_completed(fut):
        r = f.result()
        if r:
            results.append(r)
            print(f'  OK {r["room_id"]} [{r["quality"]}] {r["title"][:30]}', flush=True)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Douyu: {len(results)} 1080P streams saved", flush=True)
