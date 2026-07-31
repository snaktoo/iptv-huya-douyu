#!/usr/bin/env python3
"""
虎牙直播流实时解析播放器
用法:
  python3 hyplay.py <直播间ID或URL>
  python3 hyplay.py 23740156
  python3 hyplay.py https://www.huya.com/lpl
"""
import sys, json, subprocess, os, re, shutil

def get_room_id(text):
    """从输入中提取房间ID"""
    text = text.strip()
    # 纯数字
    if text.isdigit():
        return text
    # URL格式
    m = re.search(r'huya\.com/(\d+|\w+)', text)
    if m:
        return m.group(1)
    # 可能已经是房间号或短ID
    return text

def main():
    if len(sys.argv) < 2:
        print("用法: python3 hyplay.py <直播间ID或URL>")
        print("示例: python3 hyplay.py 23740156")
        print("示例: python3 hyplay.py https://www.huya.com/lpl")
        sys.exit(1)
    
    room = get_room_id(sys.argv[1])
    url = f"https://www.huya.com/{room}"
    
    print(f"🔍 解析虎牙直播间: {url}")
    
    # 用ykdl解析
    r = subprocess.run(['ykdl', '--info', '--json', url], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"❌ 解析失败: {r.stderr[:200]}")
        sys.exit(1)
    
    info = json.loads(r.stdout)
    title = info.get('title', '未知直播间')
    streams = info.get('streams', {})
    
    if not streams:
        print("❌ 未找到可用流")
        sys.exit(1)
    
    print(f"
📺 {title}")
    print(f"可用画质:")
    
    # 选择最佳画质（第一个通常是最高清）
    choices = []
    for i, (sname, sdata) in enumerate(sorted(streams.items(), key=lambda x: x[0] != 'BD', reverse=True)):
        profile = sdata.get('video_profile', '未知')
        src_list = sdata.get('src', [])
        if src_list:
            choices.append((sname, profile, src_list[0]))
            print(f"  [{i+1}] {sname} - {profile}")
    
    if not choices:
        print("❌ 未找到流地址")
        sys.exit(1)
    
    # 选择（默认选第一个/最高画质）
    choice = 0
    if len(choices) > 1:
        try:
            inp = input(f"
选择画质 [1-{len(choices)}] (默认1): ")
            if inp:
                choice = int(inp) - 1
                choice = max(0, min(choice, len(choices)-1))
        except:
            pass
    
    sname, profile, stream_url = choices[choice]
    print(f"
▶ 播放 {sname} - {profile}")
    print(f"  URL: {stream_url[:100]}...")
    
    # 检查是否有mpv/ffplay
    player = None
    for p in ['mpv', 'ffplay', 'vlc']:
        if shutil.which(p):
            player = p
            break
    
    if player:
        print(f"  🎬 启动 {player} 播放...")
        print(f"  (按 q 退出播放)")
        subprocess.run([player, stream_url])
    else:
        print(f"
⚠️ 未找到播放器，请安装 mpv:")
        print(f"   pkg install mpv")
        print(f"
或者直接复制以下URL到播放器中打开:")
        print(f"  {stream_url}")

if __name__ == '__main__':
    main()
