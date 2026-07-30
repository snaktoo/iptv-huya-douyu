#!/usr/bin/env python3
"""Fetch Huya streams 1080P only via API"""
import requests, json, os, sys, subprocess, re
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_FILE = "/tmp/iptv_update/huya.json"
os.makedirs("/tmp/iptv_update", exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 使用Huya API获取一起看分类全部房间(分页)
API_URL = "https://www.huya.com/cache.php?m=LiveList&do=getLiveListByPage&gameId=2135&page={}"

rooms_1080p = []

for page in range(1, 12):  # totalPage=11
    try:
        r = requests.get(API_URL.format(page), headers=headers, timeout=15)
        data = r.json()
        if data.get('status') != 200:
            break
        datas = data.get('data', {}).get('datas', [])
        if not datas:
            break
        for room in datas:
            room_id = str(room.get('profileRoom', '') or room.get('uid', ''))
            if not room_id or len(room_id) < 4:
                continue
            is_bluray = room.get('isBluRay', '0')
            if is_bluray == '1':
                rooms_1080p.append({
                    'room_id': room_id,
                    'room_name': room.get('roomName', '').strip(),
                    'nick': room.get('nick', '').strip(),
                    'bluray_mbit': room.get('bluRayMBitRate', ''),
                    'viewers': int(room.get('totalCount', '0').replace(',', '') or 0),
                    'gid': room.get('gid', ''),
                })
        blu_count = sum(1 for d in datas if d.get('isBluRay') == '1')
        print(f"Huya API page {page}: {len(datas)} rooms, {blu_count} blu-ray", flush=True)
    except Exception as e:
        print(f"Huya API page {page} error: {e}", file=sys.stderr)
        break

# 按观众数排序取前200个，提高效率同时保证质量
rooms_1080p.sort(key=lambda x: x['viewers'], reverse=True)
rooms_1080p = rooms_1080p[:200]

print(f"Huya API: {len(rooms_1080p)} blu-ray rooms selected (top200 by viewers)", flush=True)

QUAL_PRIO = ["BD6M", "BD4M", "BD"]

def get_stream(room_info):
    room_id = room_info['room_id']
    try:
        res = subprocess.run(['ykdl', '--info', '--json', f'https://www.huya.com/{room_id}'],
                           capture_output=True, text=True, timeout=20)
        out = res.stdout.strip()
        if not out:
            return None
        info = json.loads(out)
        streams = info.get('streams', {})
        if not streams:
            return None
        best = None
        for q in QUAL_PRIO:
            if q in streams:
                best = q; break
        if not best:
            return None
        s = streams[best]
        src = s.get('src', [])
        if not src:
            return None
        title = room_info['room_name'] or info.get('title', s.get('title', '')).strip()
        title = re.sub(r'[\\/:*?"<>|\t\n]', '', title)[:50]
        if not title:
            title = f"Room{room_id}"
        return {"title": title, "nick": room_info['nick'], "url": src[0], "room_id": room_id, "quality": best}
    except Exception as e:
        print(f"  Err {room_id}: {e}", file=sys.stderr)
    return None

results = []
with ThreadPoolExecutor(max_workers=10) as ex:
    fut = {ex.submit(get_stream, ri): ri for ri in rooms_1080p}
    for f in as_completed(fut):
        r = f.result()
        if r:
            results.append(r)
            print(f'  OK {r["room_id"]} [{r["quality"]}] {r["title"][:30]}', flush=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Huya: {len(results)} 1080P streams saved", flush=True)
