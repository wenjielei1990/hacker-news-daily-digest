# Hacker News Daily Digest

[在线阅读最新简报与每日归档](https://wenjielei1990.github.io/hacker-news-daily-digest/)

Nanobot 生成的 Hacker News 中文简报公开归档。GitHub Pages 只发布最终渲染的
HTML，不包含抓取正文、评论原始数据、模型输入或其他中间文件。

## 本地发布

发布当前 Nanobot workspace 中的全部时间戳报告：

```bash
python3 scripts/publish.py
```

生成站点并提交、推送到 `main`：

```bash
python3 scripts/publish.py --push
```

只发布一份已经生成的不可变快照：

```bash
python3 scripts/publish.py \
  --timestamp 2026-08-02T08-01-54-0700 \
  --push
```

指定时间戳时，脚本只复制该报告；归档首页会根据 `public/` 中已经发布
的快照重新生成，因此不会暴露其他尚未发布的本地报告。

脚本默认读取：

```text
~/.nanobot/workspace/hn_data/<timestamp>/hn_news.html
```

历史快照只会新增或更新，不会因为本地文件被清理而从公开归档中删除。

## GitHub Pages

仓库通过 `.github/workflows/pages.yml` 发布 `public/`。在 GitHub 仓库的
**Settings → Pages → Build and deployment → Source** 中选择 **GitHub Actions**。
