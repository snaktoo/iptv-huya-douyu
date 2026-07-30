#!/usr/bin/env python3
"""合并虎牙、斗鱼、央视直播源为统一M3U播放列表 — 按影视内容分类"""
import json
import os
import re
from datetime import datetime

HUYA_FILE = "/tmp/iptv_update/huya.json"
DOUYU_FILE = "/tmp/iptv_update/douyu.json"
OUTPUT_FILE = "/tmp/iptv_update/huya_douyu_movie.m3u"
FINAL_FILE = "/sdcard/Download/huya_douyu_movie.m3u"

os.makedirs("/tmp/iptv_update", exist_ok=True)

# ===== 智能内容分类器 =====
# 按优先级从高到低匹配，返回 (分类组名, 排序键)

def classify_channel(title, nick='', quality=''):
    """根据标题和昵称分析频道类别"""
    text = (title + ' ' + nick).lower()
    # 去除特殊字符和房间标识
    text_clean = re.sub(r'[「」【】『』《》\[\]\-_:：()（）！!，,。.、？?]', ' ', text)

    checks = [
        # (分类组名, 关键词列表)
        ("动漫", [
            '动漫','动画','国漫','蜡笔小新','海绵宝宝','四驱兄弟','火影','海贼王',
            '龙珠','柯南','宝可梦','数码宝贝','海贼','航海王','一拳超人','斗破苍穹',
            '斗罗大陆','全职高手','鬼灭','咒术','进击的巨人','死神','哆啦a梦','哆啦',
            '猫和老鼠','中华小当家','网球王子','七龙珠','龙珠超','精灵宝可梦',
            '樱桃小丸子','名侦探柯南','灌篮高手','圣斗士','高达','eva','奥特曼',
            '假面骑士','皮卡丘','海贼','妖尾','妖精的尾巴','全职猎人','银魂',
            'jojo','数码宝贝','神奇宝贝','口袋妖怪','宠物小精灵','一拳超人',
            '食戟','齐木','关于我转生','转生','史莱姆','overlord','fate',
            're:','re0','从零开始的','魔女','骨王','萌王','无职转生',
            '鬼灭之刃','咒术回战','进击的巨人','怪兽','机甲','萝卜番',
            '国漫','腾讯动漫','bilibili动漫','哔哩哔哩番剧','原创动画',
            '斗宗强者','萧炎','超级赛亚人','孙捂空','武魂','魂环',
            '忍道','影分身','查克拉','路飞','索隆','鸣人','佐助',
            '犬夜叉','美食的俘虏','驱魔少年','家庭教师','黑执事',
            '鲁鲁修','叛逆的','苍穹之法芙娜','魔法少女','奈叶',
            'fate','型月','月姬','空之境界','fgo','明日方舟',
            '崩坏','原神','星穹铁道','碧蓝航线','少女前线',
            '斗破','斗罗','吞噬星空','完美世界','遮天','凡人修仙',
            '仙逆','一念永恒','修罗','武动乾坤','大主宰',
            '四海鲸骑','灵笼','三体','时光代理人','伍六七',
            '狐妖小红娘','一人之下','镇魂街','刺客伍六七',
            '大王饶命','全球高考','万族之劫','诡秘之主',
            '二次元','番剧','新番','追番','漫画','漫改','轻改',
        ]),
        ("音乐", [
            '音乐','mv','kpop','女团','演唱会','点歌','歌曲','歌手','乐坛',
            '歌单','听歌','翻唱','弹唱','乐器','钢琴','吉他','乐队',
            'dj','电音','remix','hiphop','说唱','rap','民谣','流行音乐',
            '经典老歌','新歌','好歌','音乐频道','音乐台','点播','点歌台',
            '唱歌','奏乐','演奏','声乐','歌舞','舞曲','歌舞表演',
        ]),
        ("体育", [
            '斯诺克','nba','cba','中超','英超','西甲','意甲','德甲','法甲',
            '欧冠','亚冠','世界杯','奥运会','拳击','ufc','格斗','赛车','f1',
            '自行车','网球','高尔夫','乒乓球','羽毛球','台球','篮球','足球',
            '排球','橄榄球','冰球','电竞','lol','英雄联盟','王者荣耀','kpl',
            'dota','csgo','绝地求生','吃鸡','pubg','lpl','s赛','msi',
            '赛事','比赛','体育','竞技','运动','体育频道',
        ]),
        ("恐怖", [
            '恐怖','惊悚','灵异','鬼片','鬼故事','僵尸','僵尸片','林正英',
            '英叔','僵尸道长','恐怖电影','恐怖片','惊悚片','吓人','可怕',
            '血腥','暴力血腥','山村老尸','午夜凶铃','咒怨','厉鬼','鬼魂',
            '恐怖故事','怪谈','聊斋','鬼吹灯','盗墓笔记','盗墓','摸金',
            '半夜有鬼','有鬼','怨灵','凶宅','阴森','鬼屋','闹鬼',
        ]),
        ("喜剧", [
            '喜剧','搞笑','爆笑','幽默','小品','相声','脱口秀','开心','欢乐',
            '好笑','笑死','星爷','周星驰','喜剧之王','沈腾','马丽','贾玲',
            '赵本山','宋小宝','小沈阳','德云社','郭德纲','于谦','岳云鹏',
            '开心麻花','麻花','无厘头','喜剧片','欢乐喜剧人','笑傲江湖',
            '陈佩斯','朱时茂','黄渤','徐峥','王宝强','囧','泰囧',
            '憨豆','金凯瑞','搞笑剧','喜剧电影','爆笑喜剧',
            '炊事班','马大帅','彪哥','东北一家人','五福星','福星',
            '夏雪夏雨夏冰雹','爱情公寓','武林外传','家有儿女',
            '编辑部','故事','搞笑视频','欢乐','乐呵','段子',
        ]),
        ("纪录片", [
            '纪录片','纪实','探索','动物世界','国家地理','bbc','discovery',
            '舌尖上的','风味','人生一串','早餐中国','历史那些事',
            '我在故宫','如果国宝','自然','科学','宇宙','地球',
        ]),
        ("悬疑", [
            '悬疑','推理','侦探','刑侦','破案','谍战','烧脑','狄仁杰','元芳',
            '神探','福尔摩斯','悬案','心理罪','法医','探案','犯罪心理',
            '白夜追凶','隐秘的角落','沉默的真相','无证之罪','潘粤明',
            '破冰行动','人民的名义','扫黑','案发现场','鉴证','重案',
            '刑事侦缉','洗冤录','大宋提刑官','包青天','少年包青天',
            '漫长的季节','毛骗','雅贼','胡八一','破案','疑案',
            '迷案','谜案','真相','秘密','卧底','潜伏','伪装者',
        ]),
("战争/军事", [
            '军事','抗战','特种兵','战争','抗日','军人','革命','红军',
            '八路军','新四军','志愿军','亮剑','士兵突击','火蓝刀锋',
            '我的团长我的团','红海行动','战狼','长津湖','八佰',
            '大决战','解放','建国大业','建党伟业','辛亥革命',
            '雪豹','黑狐','风影','猎豹','利剑','神枪','狙击',
            '黎明之前','潜伏','伪装者','风筝','悬崖','胜算',
            '地下党','红色','谍战','铁道','游击','地雷战',
            '地道战','小兵张嘎','飞虎','特战','雷霆','突击',
            '海军','空军','陆军','部队','军营','当兵',
            '烈火','英雄','消防','救援','紧急','营救',
            '老李的意大利炮','李云龙','楚云飞','座山雕',
            '渗透','智者','硬汉','铁血','军旅','兵王',
            '特种部队','利刃','出鞘','战地','战场',
        ]),
        ("古装/武侠", [
            '古装','武侠','江湖','金庸','古龙','梁羽生','还珠格格','甄嬛',
            '芈月','大秦','大唐','大明','三国','水浒','水浒传','西游',
            '西游记','红楼梦','封神','封神榜','聊斋','新白娘子',
            '雍正','乾隆','康熙','康熙微服','还珠','如懿','延禧',
            '宫锁','步步惊心','仙剑','轩辕剑','剑侠','风云',
            '武林','天龙八部','射雕','神雕','倚天','笑傲','鹿鼎记',
            '侠客行','连城诀','碧血剑','雪山飞狐','飞狐外传',
            '楚留香','陆小凤','绝代双骄','小鱼儿','花无缺',
            '霍元甲','陈真','精武门','叶问','黄飞鸿','方世玉',
            '少林','武当','峨眉','丐帮','魔教','锦衣卫','东厂',
            '范闲','庆余年','魏璎珞','韦小宝','懿症','圣母传',
            '李淳罡','雪中悍刀行','齐天大圣','孙悟空','大圣',
            '唐三藏','唐僧','悟','水浒','梁山','108好汉',
            '喜来乐','纪晓岚','和珅','铁齿铜牙','乾隆微服',
            '唐朝','唐朝好男人','大盛魁','一代枭雄','枭雄',
            '神雕侠侣','神貂侠侣','雕侠侣','陈晓陈妍希',
            '李世民','秦始皇','汉武帝','朱元璋','崇祯',
            '大明王朝','大秦帝国','汉武大帝','康熙帝国',
            '琅琊榜','鹤唳华亭','锦绣未央','楚乔传',
            '滚滚长江','东逝水','临江仙','三国演义',
            '白鹿原','白姓鹿姓','恩怨纷争',
        ]),
        ("科幻", [
            '科幻','未来','异形','铁血战士','机械','赛博朋克','超级英雄',
            '漫威','marvel','dc','复仇者','变形金刚','星际','星球大战',
            '星球','银翼杀手','黑客帝国','终结者','阿凡达','侏罗纪',
            '哥斯拉','金刚','环太平洋','太空','宇宙','外星','穿越',
            '时间旅行','平行宇宙','奇异','黑镜','爱死机','科幻片',
        ]),
        ("动作", [
            '动作','武打','功夫','格斗','打斗','成龙','成龍','李连杰','甄子丹',
            '洪金宝','吴京','动作电影','暴力','热血','动作片','硬汉',
            '警匪','黑帮','港片动作','飞车','追捕','枪战','英雄',
            '敢死队','第一滴血','兰博','速度与激情','飙车',
            '我要打十个','叶问','刘德华','梁朝伟','周润发','赌神','赌圣',
            '反贪风暴','寒战','扫毒','使徒行者','无间道',
            '古惑仔','洪兴','铜锣湾','陈浩南',
            '港片','港产','激战','搏击','格斗技',
        ]),
        ("综艺", [
            '综艺','真人秀','跑男','极限挑战','向往的生活','歌手','中国好声音',
            '爸爸去哪儿','王牌对王牌','五哈','奔跑吧','极挑','我们的歌',
            '乘风破浪','披荆斩棘','哥哥','姐姐','明星大侦探','密室大逃脱',
            '中餐厅','亲爱的客栈','青春环游记','喜剧大赛','脱口秀大会',
            '吐槽大会','乐队的夏天','中国新说唱','这就是街舞',
            '非诚勿扰','最强大脑','一站到底','天天向上','快乐大本营',
            'running man','无限挑战','大逃脱','新西游记',
        ]),
        ("解说", [
            '解说','说电影','说剧','讲电影','速看','一口气','n分钟',
            '带你看','影评','电影解说','影视解说','几分钟看完',
            '快速看完','带你了解','深度解析','影视杂谈',
        ]),
    ]

    for category, keywords in checks:
        for kw in keywords:
            if kw in text_clean:
                return category

    # ===== 兜底：根据大范围关键词判断 =====
    # 电影类
    movie_kw = ['电影','影院','大片','4k','观影','影城','影厅','影视',
                '贺岁','王晶','导演','主演','港片','港产',
                '刘德华','梁朝伟','周润发','成龙','李连杰','甄子丹',
                '星爷','周星驰','赌神','赌圣']
    for kw in movie_kw:
        if kw in text_clean:
            return "电影"

    # 电视剧类
    tv_kw = ['剧','电视剧','追剧','连续剧','tvb','神剧','下饭','剧集',
             '韩剧','日剧','美剧','英剧','国产剧','台剧',
             '我的前半生','情满四合院','老农民','东北一家人','马大帅',
             '都挺好','苏大强','漫长的季节','你是我的荣耀',
             '欢乐颂','5个','睡在我上铺','上铺的兄弟',
             '围城','主角','剧情','年代剧',
             '这瓜保熟','刘华强','征服','狂飙']
    for kw in tv_kw:
        if kw in text_clean:
            return "电视剧"

    # 经典/怀旧
    classic_kw = ['经典','怀旧','老片','童年','回忆','老电影','重映',
                  '经典电影','怀旧剧场']
    for kw in classic_kw:
        if kw in text_clean:
            return "经典电影"

    # 爱情
    love_kw = ['爱情','恋爱','言情','甜剧','虐恋','纯爱',
               '几千年只为复活','复活妻子','挚爱','浪漫']
    for kw in love_kw:
        if kw in text_clean:
            return "爱情/情感"

    # 游戏
    game_kw = ['游戏','gaming','play','直播游戏',
               '黑神话','悟空','文化交流','游戏厅','电玩']
    for kw in game_kw:
        if kw in text_clean:
            return "游戏"

    # 无法分类的归入综合
    return "综合影视"


# ===== 央视源：从多个源库聚合，每频道提供多条备选 =====

# 多个源库地址
CCTV_SOURCE_URLS = {
    "best-fan/iptv-sources": "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_cctv.m3u8",
    "cs3306/IPTV-Sources": "https://raw.githubusercontent.com/cs3306/IPTV-Sources/main/data/output/iptv_collection.m3u",
    "BurningC4/Chinese-IPTV": "https://raw.githubusercontent.com/BurningC4/Chinese-IPTV/master/TV-IPV4.m3u",
}

# 官方保底源（已知最高720p，但广泛兼容）
OFFICIAL_SOURCES = {
    "CCTV-1": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv1_1/index.m3u8?b=200-2100",
    "CCTV-2": "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv2_1/index.m3u8?b=200-2100",
    "CCTV-3": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv3_1/index.m3u8?b=200-2100",
    "CCTV-4": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv4_1/index.m3u8?b=200-2100",
    "CCTV-5": "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv5_1/index.m3u8?b=200-2100",
    "CCTV-5+": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv5plus_1/index.m3u8?b=200-2100",
    "CCTV-6": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv6_1/index.m3u8?b=200-2100",
    "CCTV-7": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv7_1/index.m3u8?b=200-2100",
    "CCTV-8": "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv8_1/index.m3u8?b=200-2100",
    "CCTV-9": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctvjilu_1/index.m3u8?b=200-2100",
    "CCTV-10": "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv10_1/index.m3u8?b=200-2100",
    "CCTV-11": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv11_1/index.m3u8?b=200-2100",
    "CCTV-12": "https://ldocctvwbcdbd.a.bdydns.com/ldocctvwbcd/cdrmldcctv12_1/index.m3u8?b=200-2100",
    "CCTV-13": "https://ldncctvwbcdtxy.liveplay.myqcloud.com/ldncctvwbcd/cdrmldcctv13_1/index.m3u8?b=200-2100",
    "CCTV-14": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctvchild_1/index.m3u8?b=200-2100",
    "CCTV-15": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv15_1/index.m3u8?b=200-2100",
    "CCTV-16": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv16_1/index.m3u8?b=200-2100",
    "CCTV-17": "https://ldncctvwbcdbyte.volcfcdn.com/ldncctvwbcd/cdrmldcctv17_1/index.m3u8?b=200-2100",
}

# 频道显示名称映射
CCTV_NAMES = {
    "CCTV-1": "CCTV-1 综合", "CCTV1": "CCTV-1 综合",
    "CCTV-2": "CCTV-2 财经", "CCTV2": "CCTV-2 财经",
    "CCTV-3": "CCTV-3 综艺", "CCTV3": "CCTV-3 综艺",
    "CCTV-4": "CCTV-4 中文国际", "CCTV4": "CCTV-4 中文国际",
    "CCTV-5": "CCTV-5 体育", "CCTV5": "CCTV-5 体育",
    "CCTV-5+": "CCTV-5+ 体育赛事", "CCTV5+": "CCTV-5+ 体育赛事",
    "CCTV-6": "CCTV-6 电影", "CCTV6": "CCTV-6 电影",
    "CCTV-7": "CCTV-7 国防军事", "CCTV7": "CCTV-7 国防军事",
    "CCTV-8": "CCTV-8 电视剧", "CCTV8": "CCTV-8 电视剧",
    "CCTV-9": "CCTV-9 纪录", "CCTV9": "CCTV-9 纪录",
    "CCTV-10": "CCTV-10 科教", "CCTV10": "CCTV-10 科教",
    "CCTV-11": "CCTV-11 戏曲", "CCTV11": "CCTV-11 戏曲",
    "CCTV-12": "CCTV-12 社会与法", "CCTV12": "CCTV-12 社会与法",
    "CCTV-13": "CCTV-13 新闻", "CCTV13": "CCTV-13 新闻",
    "CCTV-14": "CCTV-14 少儿", "CCTV14": "CCTV-14 少儿",
    "CCTV-15": "CCTV-15 音乐", "CCTV15": "CCTV-15 音乐",
    "CCTV-16": "CCTV-16 奥林匹克", "CCTV16": "CCTV-16 奥林匹克",
    "CCTV-17": "CCTV-17 农业农村", "CCTV17": "CCTV-17 农业农村",
}

def url_matches_channel(short, url):
    """检查URL路径是否与频道编号匹配，防止频道映射错误（如CCTV-1下混入cctv14hd）"""
    url_lower = url.lower()
    # 如果URL路径中不包含cctv字样，无法校验，放行
    if '/cctv' not in url_lower and 'cctv' not in url_lower.split('/')[-1]:
        return True
    # 提取声明频道编号
    short_num = short.replace('CCTV-', '').replace('+', 'p')  # e.g. "5p" for CCTV-5+
    # 提取URL中的cctv编号
    m = re.search(r'cctv(\d+)\+?', url_lower)
    if m:
        url_num = m.group(1)
        # CCTV-5+ 特殊处理：URL中可能是 cctv5p 或 cctv5+
        if short_num == '5p':
            return url_num == '5' and ('cctv5p' in url_lower or 'cctv5+' in url_lower)
        # CCTV-5 特殊处理：排除 cctv5p (那是5+的)
        if short_num == '5' and url_num == '5':
            return 'cctv5p' not in url_lower and 'cctv5+' not in url_lower
        return url_num == short_num
    return True

def is_known_dead_source(url):
    """检查是否为已知不可用的源"""
    # ottrrs 中国移动运营商源在当前环境下全部返回空响应
    if 'ottrrs.hl.chinamobile.com' in url:
        return True
    return False

def download_m3u(name, url, local_path):
    """下载单个m3u文件"""
    import urllib.request
    try:
        print(f"  [CCTV] 从 {name} 下载...")
        urllib.request.urlretrieve(url, local_path)
        return True
    except Exception as e:
        print(f"  [CCTV] {name} 下载失败: {e}")
        return False

def parse_m3u_to_cctv(filepath, source_name):
    """
    解析 m3u 文件，提取 CCTV 频道URL，返回 {short: [(score, url)]}
    改进：优先使用 tvg-name 属性识别频道名，提高准确性
    """
    channels = {}
    if not os.path.exists(filepath):
        return channels
    current_extinf = None
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                current_extinf = line
            elif line.startswith('http') and current_extinf:
                short = None
                # 策略1：优先匹配 tvg-name 属性（最精确）
                m_tvg = re.search(r'tvg-name="CCTV[-]?(\d+\+?)"', current_extinf, re.IGNORECASE)
                if m_tvg:
                    short = 'CCTV-' + m_tvg.group(1)
                else:
                    # 策略2：匹配逗号后的显示名称
                    m_display = re.search(r',CCTV[-]?(\d+\+?)', current_extinf)
                    if m_display:
                        short = 'CCTV-' + m_display.group(1)
                    else:
                        # 策略3：任意位置匹配（兼容性）
                        m_any = re.search(r'CCTV[-]?(\d+\+?)', current_extinf)
                        if m_any:
                            short = 'CCTV-' + m_any.group(1)
                if short:
                    # 频道映射校验：URL路径必须与声明的频道名一致
                    if not url_matches_channel(short, line):
                        # 记录已过滤的映射错误（调试用）
                        pass
                        continue
                    if is_known_dead_source(line):
                        continue
                    if short not in channels:
                        channels[short] = []
                    score = 0
                    extinf_lower = current_extinf.lower()
                    if '1080p' in extinf_lower or '4k' in extinf_lower:
                        score += 100
                    if '3m1080p' in line.lower():
                        score += 80
                    if '/1080p/' in line.lower() or '1080p' in line.lower():
                        score += 70
                    if 'hd' in line.lower() or '超清' in line:
                        score += 30
                    if 'testpub' in line or 'test2025' in line:
                        score += 15
                    channels[short].append((score, line))
                current_extinf = None
    return channels

def fetch_cctv_sources():
    """
    从所有源库拉取央视源，每频道返回多条URL
    改进：URL-频道名校验 + 过滤不可用源 + 排序优化
    """
    all_cctv = {}  # short -> [(score, url, source_type)]

    # 1. 官方CDN保底（最稳定，但仅720p）
    for short, url in OFFICIAL_SOURCES.items():
        all_cctv.setdefault(short, []).append((10, url, 'official'))

    # 2. 从多个外部源库解析
    tmpdir = "/tmp/iptv_update/cctv_sources"
    os.makedirs(tmpdir, exist_ok=True)

    source_files = [
        ("best-fan/iptv-sources", f"{tmpdir}/bestfan.m3u", "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_cctv.m3u8"),
        ("cs3306/IPTV-Sources", f"{tmpdir}/cs3306_IPTV-Sources.m3u", "https://raw.githubusercontent.com/cs3306/IPTV-Sources/main/data/output/iptv_collection.m3u"),
        ("BurningC4/Chinese-IPTV", f"{tmpdir}/BurningC4.m3u", "https://raw.githubusercontent.com/BurningC4/Chinese-IPTV/master/TV-IPV4.m3u"),
    ]

    for name, local_path, remote_url in source_files:
        if not os.path.exists(local_path):
            import urllib.request
            try:
                print(f"  [CCTV] 从 {name} 下载...")
                urllib.request.urlretrieve(remote_url, local_path)
            except Exception as e:
                print(f"  [CCTV] {name} 下载失败: {e}")
                continue
        parsed = parse_m3u_to_cctv(local_path, name)
        for short, items in parsed.items():
            # 按评分降序，取前3
            items.sort(key=lambda x: -x[0])
            for score, u in items[:3]:
                all_cctv.setdefault(short, []).append((score, u, 'external'))

    # 3. 去重+排序：同域名/路径只保留最高分那条
    order = [f'CCTV-{i}' for i in range(1, 18)]
    idx_5 = order.index('CCTV-5') + 1
    order.insert(idx_5, 'CCTV-5+')

    result = []
    total_urls = 0
    for short in order:
        if short not in all_cctv:
            continue
        items = all_cctv[short]
        # 去重：相同去参路径只保留最高分
        seen = {}
        for score, url, src_type in items:
            key = url.split('?')[0]
            if key not in seen or score > seen[key][0]:
                seen[key] = (score, url, src_type)
        # 排序：高分优先（外部源在前），官方CDN放最后作为保底
        sorted_items = sorted(seen.values(), key=lambda x: (-x[0], 0 if x[2] == 'external' else 1))
        # 每个频道保留最多4条（优先外部源）
        external_urls = [u for s, u, t in sorted_items if t == 'external']
        official_urls = [u for s, u, t in sorted_items if t == 'official']
        # 外部源最多3条，官方CDN最多1条保底
        final_urls = external_urls[:3] + official_urls[:1]
        display = CCTV_NAMES.get(short, short)
        result.append((display, short, final_urls))
        total_urls += len(final_urls)

    print(f"  [CCTV] 聚合 {len(result)} 个频道，共 {total_urls} 条验后URL（已过映射校验+去重）")
    return result

# ===== 读取数据并分类 =====
def shorten_title(title):
    """简化频道名称：去装饰符号、截短"""
    s = title.strip()
    # 针对斗鱼"xxx的直播间 - yyy"格式：去掉"xxx的直播间"部分
    s = re.sub(r'^[^\-—]*?的直播间\s*[-—]\s*', '', s)
    # 针对"用户xxx的直播间 - yyy"格式
    s = re.sub(r'^用户\d+的直播间\s*[-—]\s*', '', s)
    # 去掉开头「【『《[(（等装饰符号
    s = re.sub(r'^[「【『《\[\(（]+', '', s)
    # 去掉结尾」】』》\]\)）]+装饰符号
    s = re.sub(r'[」】』》\]\)）]+$', '', s)
    # 去掉「主播名 - 」这类前缀（直到遇到第一个中文破折号/连词符前的文字）
    s = re.sub(r'^[^\-—\u4e00-\u9fff]*?[-—]\s*', '', s)
    # 去掉尾部的「 - 主播名/房间描述/后缀」
    s = re.sub(r'\s*\[.*?\]\s*$', '', s)
    # 去掉尾部「 - xxx」格式（短后缀）
    s = re.sub(r'\s*[-—]\s*(?=[a-zA-Z0-9\u4e00-\u9fff]{0,6}$)', '', s)
    # 清理残留的单边装饰符号
    s = re.sub(r'[「」【】『』《》\[\]\(\)（）]', '', s)
    # 去掉重复内容（如"米尼影院经典电视剧米尼影院"→"米尼影院经典电视剧"）
    # 如果后半段和前半段一样，去重
    s = re.sub(r'^(.{3,}?)\1$', r'\1', s)
    # 去掉多余空格
    s = re.sub(r'\s+', ' ', s).strip()
    if not s:
        s = title.strip()[:20]
    return s[:25]

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
        # 简化quality标记
        q_short = quality.replace('原画', '').replace('蓝光', '').strip()
        short = shorten_title(title)
        display = f"{short} [{q_short}]" if q_short else short
        cat = classify_channel(title, nick, quality)
        channels.append((cat, display, url, quality))
    return channels

huya_channels = load_and_classify(HUYA_FILE, "Huya")
douyu_channels = load_and_classify(DOUYU_FILE, "Douyu")

# ===== 获取央视源（从多个源库聚合，每频道多条备选） =====
CCTV_CHANNELS = fetch_cctv_sources()  # [(显示名, 短名, [URL列表])]

# ===== 按分类组名排序输出 =====
# 自定义分类显示顺序
CAT_ORDER = [
    "央视", "电影", "经典电影", "电视剧", "动漫", "综艺", "音乐", "体育",
    "喜剧", "恐怖", "动作", "古装/武侠", "悬疑", "科幻",
    "战争/军事", "纪录片", "解说", "爱情/情感", "游戏", "综合影视"
]

def cat_sort_key(cat):
    try:
        return CAT_ORDER.index(cat)
    except ValueError:
        return 999

lines = []
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
lines.append('#EXTM3U')
lines.append(f'# 综合IPTV直播源 (央视 + 虎牙1080P + 斗鱼1080P)')
lines.append(f'# 生成时间: {now_str}')
lines.append('# 来源: 多源库聚合(best-fan + cs3306 + BurningC4 + 官方CDN) | 虎牙一起看分类 | 斗鱼一起看分类')
lines.append('# 清晰度: 央视多源备选（优先1080p，支持切换） / 虎牙1080P蓝光 / 斗鱼1080P原画')
lines.append('# 自动更新: GitHub Actions 每30分钟')
lines.append('# 分类: 按影视内容类型自动归类')
lines.append('')

# 构建分类→频道映射
# 按来源分组：央视 / 虎牙 / 斗鱼
source_map = {}

# 央视（每频道多条备选，同名不同URL）
for name, _, urls in CCTV_CHANNELS:
    for url in urls:
        source_map.setdefault("央视", []).append((name, url))

# 虎牙：带影视分类标签
for cat, display, url, quality in huya_channels:
    tagged = f"[{cat}] {display}" if cat not in ("综合影视",) else display
    source_map.setdefault("虎牙", []).append((tagged, url))

# 斗鱼：带影视分类标签
for cat, display, url, quality in douyu_channels:
    tagged = f"[{cat}] {display}" if cat not in ("综合影视",) else display
    source_map.setdefault("斗鱼", []).append((tagged, url))

# 按 央视 → 虎牙 → 斗鱼 顺序输出
source_order = ["央视", "虎牙", "斗鱼"]

for src in source_order:
    channels = source_map.get(src, [])
    if not channels:
        continue
    lines.append('')
    lines.append(f'# ===== {src} =====')
    lines.append('')
    for display, url in channels:
        lines.append(f'#EXTINF:-1 group-title="{src}" tvg-name="{display}",{display}')
        lines.append(url)

content = '\n'.join(lines)

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

import shutil
os.makedirs(os.path.dirname(FINAL_FILE), exist_ok=True)
if os.path.exists(FINAL_FILE):
    os.remove(FINAL_FILE)
shutil.copy2(OUTPUT_FILE, FINAL_FILE)

cctv_count = sum(len(urls) for _, _, urls in CCTV_CHANNELS)
huya_count = len(huya_channels)
douyu_count = len(douyu_channels)

print(f"M3U: Generated {OUTPUT_FILE}")
print(f"  ️央视: {cctv_count} channels ({len(CCTV_CHANNELS)}个频道, 每频道多备选源)")
print(f"  虎牙: {huya_count} channels (1080P蓝光)")
print(f"  斗鱼: {douyu_count} channels (1080P原画)")
print(f"  总计: {cctv_count + huya_count + douyu_count} channels")
print(f"  分组: 央视 / 虎牙 / 斗鱼（频道名前带[影视分类]标签）")
print(f"  Saved to: {FINAL_FILE}")
