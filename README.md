# 虎牙+斗鱼 影视轮播IPTV直播源

自动抓取虎牙「一起看」和斗鱼「一起看」分类下的影视轮播直播间流地址，生成 IPTV 格式的 M3U 播放列表。

## 特点

- **每30分钟自动更新**（通过 GitHub Actions）
- **虎牙**：116+ 个影视轮播频道，HLS (m3u8) 格式
- **斗鱼**：29+ 个影视轮播频道，FLV 格式
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

## 本地使用

也支持在本地运行：

```bash
# 安装依赖
pip install requests ykdl

# 抓取虎牙流
python scripts/fetch_huya.py

# 抓取斗鱼流
python scripts/fetch_douyu.py

# 合并生成 M3U
python scripts/merge_m3u.py
```

生成的文件位于 `/tmp/iptv_update/huya_douyu_movie.m3u`

## 注意

- 所有流地址均有**时效性**（通常 2~24 小时过期）
- 斗鱼流地址包含 `wsAuth` 和 `token` 参数，到期需重新抓取
- 虎牙流地址包含 `wsSecret` 和 `wsTime` 参数，同样有时效性
- GitHub Actions 每30分钟自动更新一次，确保地址新鲜

## 目录结构

```
.
├── .github/workflows/update.yml  # GitHub Actions 工作流配置
├── scripts/
│   ├── fetch_huya.py             # 虎牙流地址抓取
│   ├── fetch_douyu.py            # 斗鱼流地址抓取
│   └── merge_m3u.py              # 合并生成 M3U 播放列表
└── README.md
```