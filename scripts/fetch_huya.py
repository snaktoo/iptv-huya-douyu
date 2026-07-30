#!/usr/bin/env python3
"""Fetch Huya streams from Yiqikan category"""
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    r = requests.get("https://www.huya.com/g/2135", headers=headers, timeout=15)
    html = r.text
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

room_ids = set()
for m in re.finditer(r"https?://(?:www\.)?huya\.com/(\d+)", html):
    rid = m.group(1)
    if len(rid) >= 4:
        room_ids.add(rid)

print(f"Huya: Found {len(room_ids)} room IDs", flush=True)

results = []
headers_m = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 Mobile"
}

def get_stream(room_id):
    try:
        r = requests.get(f"https://m.huya.com/{room_id}", headers=headers_m, timeout=10)
        html = r.text
        title = (re.search(r'"sRoomName"\s*:\s*"([^"]+)"', html) or [None, "Unknown"])[1]
        nick = (re.search(r'"sNick"\s*:\s*"([^"]+)"', html) or [None, "Unknown"])[1]
        ll_match = re.search(r'"liveLineUrl"\s*:\s*"([^"]+)"', html)
        if ll_match:
            decoded = base64.b64decode(ll_match.group(1)).decode("utf-8")
            url = "https:" + decoded if decoded.startswith("/") else decoded
            title = re.sub(r'[\/:*?"<>|]', "", title.replace("\t","").replace("\n","").strip())
            return {"title": title, "nick": nick, "url": url, "room_id": room_id}
    except Exception as e:
        print(f"  Error {room_id}: {e}", file=sys.stderr)
    return None

with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(get_stream, rid): rid for rid in room_ids}
    for f in as_completed(futures):
        r = f.result()
        if r:
            results.append(r)
            print(f'  OK {r["room_id"]} - {r["title"][:30]}', flush=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"Huya: {len(results)} valid streams", flush=True)
