#!/usr/bin/env python3
"""抓取虎牙一起看分类下所有直播间的流地址"""
import requests
import re
import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_FILE = "/tmp/iptv_update/huya.json"
os.makedirs("/tmp/iptv_update", exist_ok=True)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 获取虎牙一起看分类页面中的房间ID
url = 'https://www.huya.com/g/2135'
r = requests.get(url, headers=headers, timeout=15)
html = r.text

# 从页面中提取房间ID，格式: https://www.huya.com/{room_id}
room_ids = set()
for m in re.finditer(r'https?://(?:www\.)?huya\.com/(\d+)', html):
    rid = m.group(1)
    if len(rid) >= 4:  # 至少4位数字
        room_ids.add(rid)

print(f"Huya: Found {len(room_ids)} room IDs")

results = []
headers_m = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
}

def get_huya_stream(room_id):
    try:
        r = requests.get(f'https://m.huya.com/{room_id}', headers=headers_m, timeout=10)
        html = r.text
        
        title_match = re.search(r'"sRoomName"\s*:\s*"([^"]+)"', html)
        title = title_match.group(1) if title_match else 'Unknown'
        
        nick_match = re.search(r'"sNick"\s*:\s*"([^"]+)"', html)
        nick = nick_match.group(1) if nick_match else 'Unknown'
        
        live_line_match = re.search(r'"liveLineUrl"\s*:\s*"([^"]+)"', html)
        live_line_url = None
        if live_line_match:
            try:
                decoded = base64.b64decode(live_line_match.group(1)).decode('utf-8')
                live_line_url = 'https:' + decoded if decoded.startswith('/') else decoded
            except Exception as e:
                print(f"  Decode error {room_id}: {e}", file=sys.stderr)
        
        if live_line_url:
            title_clean = title.replace('\\t', '').replace('\\n', '').strip()
            title_clean = re.sub(r'[\\/:*?"<>|]', '', title_clean)
            return {"title": title_clean, "nick": nick, "url": live_line_url, "room_id": room_id}
    except Exception as e:
        print(f"  Error {room_id}: {e}", file=sys.stderr)
    return None

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(get_huya_stream, rid): rid for rid in room_ids}
    for future in as_completed(futures):
        result = future.result()
        if result:
            results.append(result)
            print(f"  ✓ {result['room_id']} - {result['title'][:30]}")
        else:
            pass  # 未开播或无流

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Huya: Got {len(results)} valid streams, saved to {OUTPUT_FILE}")