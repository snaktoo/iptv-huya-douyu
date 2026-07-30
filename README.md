# 综合IPTV直播源 — 央视 + 虎牙1080P + 斗鱼1080P

自动抓取央视总台官方频道、虎牙「一起看」和斗鱼「一起看」分类下的影视轮播直播间流地址，生成统一的 IPTV 格式 M3U 播放列表。

## 特点

- **每30分钟自动更新**（通过 GitHub Actions）
- **央视总台**：18个官方频道（CCTV-1 ~ CCTV-17 + CCTV-5+），720p HLS 流
- **虎牙**：185+ 个1080P蓝光影视轮播频道（BD6M/BD4M/BD），FLV 格式
- **斗鱼**：113+ 个1080P影视轮播频道（原画1080P/蓝光4M），FLV 格式
- **总计**：316+ 频道，全部为1080P（央视720p）
- **全自动**：无需手动操作，仓库自动抓取、合并、推送

## 播放列表地址

```
https://raw.githubusercontent.com/你的用户名/iptv-huya-douyu/main/huya_douyu_movie.m3u
```

## 部署到自己的 GitHub

1. **创建新仓库** → 点右上角 `+` → `New repository`
   - 仓库名: `iptv-huya-douyu`
   - 设为 **Public**（公开才能获取 Raw URL）

2. **上传文件**：将本项目所有文件推送上去

3. **启用 Actions**：
   - 进入仓库 → `Actions` 标签
   - 点击 `I understand my workflows, go ahead and enable them`
   - 工作流会自动按计划运行（每30分钟）

4. **获取播放地址**：
   - 更新后的 M3U 文件会推送到仓库
   - 访问 `https://raw.githubusercontent.com/你的用户名/iptv-huya-douyu/main/huya_douyu_movie.m3u`
   - 替换 `你的用户名` 为你的 GitHub 用户名

## 频道统计

| 来源 | 频道数 | 画质 | 更新方式 |
|------|--------|------|----------|
| 央视总台 | 18 | 720p（官方CDN） | 静态硬编码 |
| 虎牙一起看 | 185+ | 1080P（BD6M/BD4M/BD） | API + ykdl 每30分钟 |
| 斗鱼一起看 | 113+ | 1080P（原画1080P/蓝光4M） | ykdl 每30分钟 |
| **总计** | **316+** | **全高清** | **自动更新** |

## 画质说明

### 央视
- 来源：央视网 tv.cctv.com/live 官方播放页，火山引擎/腾讯云 CDN
- 画质：720p（央视官方最高免费画质）
- 特点：HLS（.m3u8）格式，长期有效

### 虎牙
- 来源：虎牙 API 筛选 `isBluRay=1` 的房间
- 画质：BD6M（蓝光6Mbps）> BD4M（蓝光4Mbps）> BD（蓝光）
- 标识：频道名包含 `[BD6M]` / `[BD4M]` / `[BD]`

### 斗鱼
- 来源：斗鱼一起看分类 → 影视筛选 → 1080P过滤
- 画质：原画1080P60 > 原画1080P30 > 蓝光4M > 原画1080P20
- 标识：频道名包含 `[原画1080P..]` / `[蓝光]`

## 本地使用

```bash
# 安装依赖
pip install requests ykdl

# 抓取虎牙流
python scripts/fetch_huya.py

# 抓取斗鱼流
python scripts/fetch_douyu.py

# 合并生成 M3U（包含央视+虎牙+斗鱼）
python scripts/merge_m3u.py
```

生成的文件位于 `/tmp/iptv_update/huya_douyu_movie.m3u`（也会同步到 `/sdcard/Download/`）

## 注意

- 虎牙和斗鱼的流地址均有**时效性**（通常 2~24 小时过期），需定期更新
- 虎牙流地址包含 `wsSecret` 和 `wsTime` 参数
- 斗鱼流地址包含 `wsAuth` 和 `token` 参数
- GitHub Actions 每30分钟自动更新一次，确保地址新鲜
- 央视地址为官方 CDN 直链，稳定长期有效

## 目录结构

```
.
├── .github/workflows/update.yml  # GitHub Actions 工作流配置
├── scripts/
│   ├── fetch_huya.py             # 虎牙流地址抓取（API + ykdl）
│   ├── fetch_douyu.py            # 斗鱼流地址抓取（ykdl）
│   └── merge_m3u.py              # 合并央视+虎牙+斗鱼生成M3U
├── huya_douyu_movie.m3u          # 生成的播放列表（已更新至仓库）
└── README.md
```