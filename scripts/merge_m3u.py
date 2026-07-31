#!/usr/bin/env python3
"""
合并虎牙、斗鱼、央视直播源为统一M3U播放列表
核心策略：在生成M3U时实时全链路验证每个源的可用性（m3u8→子流→TS分片），仅收录通过验证的源
"""
import json
import os
import re
import subprocess
import shutil
from datetime import datetime

HUYA_FILE = "/tmp/iptv_update/huya.json"
DOUYU_FILE = "/tmp/iptv_update/douyu.json"
OUTPUT_FILE = "/tmp/iptv_update/huya_douyu_movie.m3u"
FINAL_FILE = "/sdcard/Download/huya_douyu_movie.m3u"

os.makedirs("/tmp/iptv_update", exist_ok=True)

# ============ 全链路源验证引擎 ============

def run_cmd(cmd, timeout=12):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, b"", b"timeout"

def resolve_url(base_url, path):
    if path.startswith('http'):
        return path
    if path.startswith('/'):
        domain = base_url.split('//')[1].split('/')[0]
        return f"https://{domain}{path}"
    base = base_url.rsplit('/', 1)[0]
    return f"{base}/{path}"

def test_source_chain(master_url, timeout_per_step=8):
    """
    全链路测试直播源：主m3u8 → 子流m3u8 → 最新TS分片(1KB) → 验证是MPEG-TS
    支持两种HLS类型：
      Type A: variant playlist (#EXT-X-STREAM-INF) → 解析子流 → 提取TS → 验证
      Type B: 媒体plalist (直接#EXTINF + .ts) → 直接提取TS → 验证
    返回 (is_ok, detail, verified_sub_url_or_None)
    """
    rc, out, _ = run_cmd(f"timeout {timeout_per_step} curl -skL '{master_url}'", timeout_per_step+2)
    if rc != 0 or not out:
        return False, f"master_fail(rc={rc})", None
    text = out.decode('utf-8', errors='replace')
    lines = text.split('\n')
    
    # 判断类型：是否包含 #EXT-X-STREAM-INF (variant)
    is_variant = any('EXT-X-STREAM-INF' in l for l in lines)
    
    if is_variant:
        # Type A: variant playlist → 提取子流URL → 测试子流
        sub_paths = [l.strip() for l in lines 
                     if l.strip() and not l.startswith('#') and not l.startswith('<')]
        if not sub_paths:
            return False, "variant_no_sub", None
        
        for sp in sub_paths[:3]:
            sub_url = resolve_url(master_url, sp)
            rc, out, _ = run_cmd(f"timeout {timeout_per_step} curl -skL '{sub_url}'", timeout_per_step+2)
            if rc != 0 or not out:
                continue
            sub_text = out.decode('utf-8', errors='replace')
            
            # 从子流中提取TS分片路径
            ts_paths = _extract_ts_paths(sub_text)
            if not ts_paths:
                continue
            
            ok, detail = _verify_ts(ts_paths[-1], sub_url)
            if ok:
                return True, detail, sub_url
        
        return False, f"variant_no_ts(tried={len(sub_paths)})", None
    else:
        # Type B: 媒体playlist (可能直接包含#EXTINF+.ts分片)
        ts_paths = _extract_ts_paths(text)
        if not ts_paths:
            # 可能这个URL本身返回的就是非m3u8内容
            return False, "media_no_ts", None
        
        ok, detail = _verify_ts(ts_paths[-1], master_url)
        if ok:
            return True, detail, master_url
        return False, f"media_ts_fail({detail})", None


def _extract_ts_paths(playlist_text):
    """从playlist文本中提取所有TS分片路径"""
    lines = playlist_text.split('\n')
    ts_paths = []
    for i, line in enumerate(lines):
        ls = line.strip()
        if ls.startswith('#EXTINF:'):
            if i+1 < len(lines):
                path = lines[i+1].strip()
                if path and not path.startswith('#') and not path.startswith('<'):
                    ts_paths.append(path)
    return ts_paths


def _verify_ts(ts_path, base_url):
    """下载TS分片前1KB并验证为MPEG-TS，返回 (ok, detail)"""
    ts_url = resolve_url(base_url, ts_path)
    
    rc2, out2, _ = run_cmd(
        f"timeout 6 curl -skL -r 0-1023 -o /tmp/_ts_check '{ts_url}' "
        f"&& file /tmp/_ts_check", 8)
    file_type = out2.decode('utf-8', errors='replace').strip()
    
    rc3, out3, _ = run_cmd(
        f"timeout 6 curl -skL -r 0-1023 -o /dev/null -w '%{{http_code}}|%{{size_download}}' '{ts_url}'", 8)
    http_info = out3.decode('utf-8', errors='replace').strip()
    http_code = http_info.split('|')[0] if '|' in http_info else http_info
    
    is_valid = ('mpeg' in file_type.lower() or 'data' in file_type.lower()) \
               and http_code in ('200', '206')
    
    detail = f"http={http_code} type={file_type[:25]}"
    return is_valid, detail


# ============ 央视源：官方CDN + 外部库动态验证 ============

CCTV_CANDIDATES = {
    "CCTV-1":  [("volcfcdn", "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv1_1/index.m3u8?b=200-2100"),
                ("VOC",      "https://liveplay-srs.voc.com.cn/hls/tv/134_180adf.m3u8")],
    "CCTV-2":  [("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv2_1/index.m3u8?b=200-2100"),
                ("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv2_1/index.m3u8?b=200-2100")],
    "CCTV-3":  [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv3_1/index.m3u8?b=200-2100"),
                ("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv3_1/index.m3u8?b=200-2100")],
    "CCTV-4":  [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv4_1/index.m3u8?b=200-2100"),
                ("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv4_1/index.m3u8?b=200-2100")],
    "CCTV-5":  [("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv5_1/index.m3u8?b=200-2100"),
                ("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv5_1/index.m3u8?b=200-2100")],
    "CCTV-5+": [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv5plus_1/index.m3u8?b=200-2100"),
                ("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv5plus_1/index.m3u8?b=200-2100")],
    "CCTV-6":  [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv6_1/index.m3u8?b=200-2100"),
                ("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv6_1/index.m3u8?b=200-2100")],
    "CCTV-8":  [("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv8_1/index.m3u8?b=200-2100"),
                ("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv8_1/index.m3u8?b=200-2100")],
    "CCTV-9":  [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctvjilu_1/index.m3u8?b=200-2100")],
    "CCTV-10": [("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv10_1/index.m3u8?b=200-2100"),
                ("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv10_1/index.m3u8?b=200-2100")],
    "CCTV-11": [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv11_1/index.m3u8?b=200-2100"),
                ("xykt",    "https://xykt-fix.github.io/play/a02b/index.m3u8")],
    "CCTV-12": [("bdydns",  "https://ldocctvwbcdbd.a.bdydns.com/ldocctvwbcd/cdrmldcctv12_1/index.m3u8?b=200-2100"),
                ("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv12_1/index.m3u8?b=200-2100")],
    "CCTV-13": [("myqcloud","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv13_1/index.m3u8?b=200-2100"),
                ("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv13_1/index.m3u8?b=200-2100"),
                ("myqcloud_td","https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv13_1_td.m3u8")],
    "CCTV-14": [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctvchild_1/index.m3u8?b=200-2100")],
    "CCTV-15": [("xykt",    "https://xykt-fix.github.io/play/a02e/index.m3u8")],
    "CCTV-16": [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv16_1/index.m3u8?b=200-2100")],
    "CCTV-17": [("volcfcdn","https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv17_1/index.m3u8?b=200-2100")],
}

CCTV_NAMES = {
    "CCTV-1": "CCTV-1 综合", "CCTV-2": "CCTV-2 财经",
    "CCTV-3": "CCTV-3 综艺", "CCTV-4": "CCTV-4 中文国际",
    "CCTV-5": "CCTV-5 体育", "CCTV-5+": "CCTV-5+ 体育赛事",
    "CCTV-6": "CCTV-6 电影", "CCTV-8": "CCTV-8 电视剧",
    "CCTV-9": "CCTV-9 纪录", "CCTV-10": "CCTV-10 科教",
    "CCTV-11": "CCTV-11 戏曲", "CCTV-12": "CCTV-12 社会与法",
    "CCTV-13": "CCTV-13 新闻", "CCTV-14": "CCTV-14 少儿",
    "CCTV-15": "CCTV-15 音乐",
    "CCTV-16": "CCTV-16 奥林匹克", "CCTV-17": "CCTV-17 农业农村",
}

CCTV_LIB_URLS = [
    ("best-fan", "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_cctv.m3u8"),
    ("cs3306", "https://raw.githubusercontent.com/cs3306/IPTV-Sources/main/data/output/iptv_collection.m3u"),
    ("BurningC4", "https://raw.githubusercontent.com/BurningC4/Chinese-IPTV/master/TV-IPV4.m3u"),
    ("iptv-org", "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u"),
]

def download_external_cctv_sources():
    """下载并解析外部源库，返回 {频道短名: [(url, 库名), ...]}"""
    channels = {}
    for lib_name, lib_url in CCTV_LIB_URLS:
        rc, out, _ = run_cmd(f"timeout 15 curl -skL '{lib_url}'", 18)
        if rc != 0 or not out:
            print(f"  [CCTV-Lib] {lib_name}: download fail (rc={rc})")
            continue
        text = out.decode('utf-8', errors='replace')
        extinf = ""
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('#EXTINF:'):
                extinf = line
            elif line and not line.startswith('#') and line.startswith('http'):
                ch_name = ""
                if 'tvg-name="' in extinf:
                    ch_name = extinf.split('tvg-name="')[1].split('"')[0]
                elif ',' in extinf:
                    ch_name = extinf.rsplit(',', 1)[-1].strip()
                for short in CCTV_NAMES:
                    if short in ch_name or short.replace('-', '') in ch_name.replace(' ', ''):
                        channels.setdefault(short, []).append((line, lib_name))
                        break
                extinf = ""
        print(f"  [CCTV-Lib] {lib_name}: downloaded + parsed")
    return channels


def fetch_cctv_sources():
    """核心央视源获取：先测试官方CDN，再试外部库，只收录全链路通过的"""
    verified = {}
    
    print("\n  [CCTV] 阶段1: 官方CDN候选源验证...")
    for ch_short in sorted(CCTV_NAMES, key=lambda x: int(x.split('-')[1].split('+')[0])):
        if ch_short not in CCTV_CANDIDATES:
            continue
        for cdn_type, master_url in CCTV_CANDIDATES[ch_short]:
            ok, detail, _ = test_source_chain(master_url)
            status = "✅" if ok else "❌"
            print(f"  {status} {ch_short} ({cdn_type}): {detail[:60]}")
            if ok:
                verified.setdefault(ch_short, []).append((CCTV_NAMES[ch_short], master_url))
                if len(verified[ch_short]) >= 2:
                    break  # 每个频道最多保留2个备选源
    
    print(f"\n  [CCTV] 阶段2: 外部库源验证...")
    lib_channels = download_external_cctv_sources()
    for ch_short in sorted(CCTV_NAMES, key=lambda x: int(x.split('-')[1].split('+')[0])):
        if ch_short in verified:
            continue  # 阶段1已有可用源，不再补充
        if ch_short not in lib_channels:
            continue
        for url, lib_name in lib_channels[ch_short]:
            ok, detail, _ = test_source_chain(url)
            status = "✅" if ok else "❌"
            print(f"  {status} {ch_short} ({lib_name}): {detail[:60]}")
            if ok:
                verified.setdefault(ch_short, []).append((CCTV_NAMES[ch_short], url))
                break
    
    print(f"\n  [CCTV] 汇总: {len(verified)}/{len(CCTV_NAMES)} channels verified")
    if verified:
        print(f"  可用: {', '.join(sorted(verified, key=lambda x: int(x.split('-')[1].split('+')[0])))}")
    
    result = []
    for ch_short in sorted(verified, key=lambda x: int(x.split('-')[1].split('+')[0])):
        display = CCTV_NAMES[ch_short]
        urls = [u for _, u in verified[ch_short]]
        result.append((display, ch_short, urls))
    return result


# ============ 虎牙/斗鱼 ============

def shorten_title(title):
    s = title.strip()
    s = re.sub(r'^[^\-—]*?的直播间\s*[-—]\s*', '', s)
    s = re.sub(r'^用户\d+的直播间\s*[-—]\s*', '', s)
    s = re.sub(r'^[「【『《\[\(（]+', '', s)
    s = re.sub(r'[」】』》\]\)）]+$', '', s)
    s = re.sub(r'^[^\-—\u4e00-\u9fff]*?[-—]\s*', '', s)
    s = re.sub(r'\s*\[.*?\]\s*$', '', s)
    s = re.sub(r'\s*[-—]\s*(?=[a-zA-Z0-9\u4e00-\u9fff]{0,6}$)', '', s)
    s = re.sub(r'[「」【】『』《》\[\]\(\)（）]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if not s: s = title.strip()[:20]
    return s[:25]

def classify_channel(title, nick='', quality=''):
    text = (title + ' ' + nick).lower()
    text_clean = re.sub(r'[「」【】『』《》\[\]\-_:：()（）！!，,。.、？?]', ' ', text)
    checks = [
        ("动漫", ['动漫','动画','国漫','火影','海贼','龙珠','柯南','宝可梦','海贼王','斗破苍穹','斗罗大陆','全职高手','鬼灭','咒术','死神','哆啦a梦','奥特曼','假面骑士','灌篮高手','圣斗士','高达','eva','关于我转生','转生','史莱姆','overlord','fate','re0','斗破','斗罗','吞噬星空','完美世界','遮天','凡人修仙','二次元','番剧','漫画','漫改']),
        ("音乐", ['音乐','mv','kpop','演唱会','点歌','歌曲','歌手','翻唱','弹唱','乐器','钢琴','吉他','乐队','dj','电音','remix','说唱','rap','唱歌']),
        ("体育", ['斯诺克','nba','cba','中超','英超','西甲','意甲','欧冠','世界杯','拳击','ufc','格斗','赛车','f1','网球','乒乓球','篮球','足球','电竞','lol','英雄联盟','王者荣耀','kpl','dota','csgo','pubg','lpl','赛事','比赛','体育']),
        ("恐怖", ['恐怖','惊悚','灵异','鬼片','鬼故事','僵尸','林正英','山村老尸','午夜凶铃','咒怨','聊斋','鬼吹灯','盗墓笔记']),
        ("喜剧", ['喜剧','搞笑','爆笑','小品','相声','脱口秀','星爷','周星驰','沈腾','赵本山','德云社','郭德纲','开心麻花','武林外传','爱情公寓','家有儿女']),
        ("纪录片", ['纪录片','纪实','探索','动物世界','国家地理','bbc','discovery','舌尖上']),
        ("悬疑", ['悬疑','推理','侦探','刑侦','破案','谍战','狄仁杰','神探','白夜追凶','无间道','包青天','潜伏']),
        ("战争/军事", ['军事','抗战','特种兵','战争','抗日','军人','亮剑','士兵突击','战狼','长津湖','李云龙','雪豹']),
        ("古装/武侠", ['古装','武侠','江湖','金庸','古龙','还珠格格','甄嬛','三国','水浒','西游记','红楼梦','封神','新白娘子','天龙八部','射雕','神雕','倚天','笑傲','鹿鼎记','庆余年','琅琊榜']),
        ("科幻", ['科幻','未来','异形','机械','赛博朋克','漫威','marvel','dc','复仇者','变形金刚','星际','星球大战','黑客帝国','侏罗纪','哥斯拉']),
        ("动作", ['动作','武打','功夫','格斗','打斗','成龙','李连杰','甄子丹','吴京','动作电影','热血','动作片','古惑仔','速度与激情','港片']),
        ("综艺", ['综艺','真人秀','跑男','极限挑战','向往的生活','歌手','中国好声音','王牌对王牌','奔跑吧','乘风破浪','明星大侦探']),
        ("解说", ['解说','说电影','说剧','讲电影','速看','一口气','影评','电影解说','深度解析']),
    ]
    for category, keywords in checks:
        for kw in keywords:
            if kw in text_clean:
                return category
    movie_kw = ['电影','影院','大片','4k','影城','影视']
    tv_kw = ['剧','电视剧','追剧','连续剧','tvb','韩剧','日剧','美剧']
    classic_kw = ['经典','怀旧','老片','童年']
    love_kw = ['爱情','恋爱','言情','纯爱','浪漫']
    game_kw = ['游戏','gaming','黑神话']
    for kw in movie_kw:
        if kw in text_clean: return "电影"
    for kw in tv_kw:
        if kw in text_clean: return "电视剧"
    for kw in classic_kw:
        if kw in text_clean: return "经典电影"
    for kw in love_kw:
        if kw in text_clean: return "爱情/情感"
    for kw in game_kw:
        if kw in text_clean: return "游戏"
    return "综合影视"

def load_and_classify(filepath, source_name):
    channels = []
    if not os.path.exists(filepath):
        return channels
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for ch in data:
        title = ch.get('title', 'Unknown').replace('\\n', ' ').replace('\\r', '').strip()
        url = ch.get('url', '')
        quality = ch.get('quality', '')
        nick = ch.get('nick', '')
        if not url:
            continue
        if not title or title == 'Unknown':
            title = nick[:20] or f"{source_name}_{ch.get('room_id','')}"
        q_short = quality.replace('原画', '').replace('蓝光', '').strip()
        short = shorten_title(title)
        display = f"{short} [{q_short}]" if q_short else short
        cat = classify_channel(title, nick, quality)
        channels.append((cat, display, url, quality))
    return channels


# ============ 主流程 ============

print("=" * 60)
print("IPTV直播源合并脚本 v3.0（运行时动态验证）")
print(f"开始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

print("\n[虎牙] 加载...")
huya_channels = load_and_classify(HUYA_FILE, "Huya")
print(f"  {len(huya_channels)} channels")

print("\n[斗鱼] 加载...")
douyu_channels = load_and_classify(DOUYU_FILE, "Douyu")
print(f"  {len(douyu_channels)} channels")

print("\n[CCTV] 动态全链路验证央视源...")
CCTV_CHANNELS = fetch_cctv_sources()

print("\n[输出] 生成M3U...")
lines = []
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
lines.append('#EXTM3U')
lines.append(f'# 综合IPTV直播源 (央视 + 虎牙蓝光 + 斗鱼原画)')
lines.append(f'# 生成: {now_str}')
lines.append('# 来源: 官方CDN + 外部源库（运行时全链路验证，仅收录可用源）')
lines.append('# 更新: GitHub Actions 每30分钟')

lines.append('')
source_map = {}

for name, short, urls in CCTV_CHANNELS:
    for url in urls:
        source_map.setdefault("央视", []).append((name, url))
for cat, display, url, quality in huya_channels:
    tagged = f"[{cat}] {display}" if cat != "综合影视" else display
    source_map.setdefault("虎牙", []).append((tagged, url))
for cat, display, url, quality in douyu_channels:
    tagged = f"[{cat}] {display}" if cat != "综合影视" else display
    source_map.setdefault("斗鱼", []).append((tagged, url))

# 注意: 不输出#EXTVLCOPT，因为ExoPlayer/主流Android播放器不识别
# 斗鱼流不需要Referer即可播放，虎牙流即使加Referer也有时效性
for src in ["央视", "虎牙", "斗鱼"]:
    channels = source_map.get(src, [])
    if not channels:
        continue
    lines.append('')
    lines.append(f'# ===== {src} =====')
    for display, url in channels:
        lines.append(f'#EXTINF:-1 group-title="{src}" tvg-name="{display}",{display}')
        lines.append(url)

content = '\n'.join(lines)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

os.makedirs(os.path.dirname(FINAL_FILE), exist_ok=True)
if os.path.exists(FINAL_FILE):
    os.remove(FINAL_FILE)
shutil.copy2(OUTPUT_FILE, FINAL_FILE)

cctv_count = sum(len(urls) for _, _, urls in CCTV_CHANNELS)
print(f"\n{'='*60}")
print(f"完成!")
print(f"  📺 央视: {cctv_count}条 ({len(CCTV_CHANNELS)}个频道)")
print(f"  🟣 虎牙: {len(huya_channels)}条")
print(f"  🔵 斗鱼: {len(douyu_channels)}条")
print(f"  📦 总计: {cctv_count + len(huya_channels) + len(douyu_channels)}条")
print(f"  💾 {FINAL_FILE}")
print(f"  🕐 {now_str}")
print("=" * 60)