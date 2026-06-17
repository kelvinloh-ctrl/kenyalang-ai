---
name: kenyalang-scout
description: 抓全球 AI 产业新闻并产出可读的 brief。用在 Kenyalang.AI（每日早 brief / 周 digest / 按需 Q&A）+ 未来其他情报 Agent（Kenyalang.Fit 健身竞品 / Bijak 营销文案选题等）。Trigger when 用户说「跑 AI 早报」「跑 brief」「scout AI 新闻」「Kenyalang」「AI weekly digest」。
---

你在跑 Kenyalang 情报抓取流程。这只犀鸟做一件事：**在嘈杂的 AI 信息流里挑出真值得报的 5-8 条**。

## 核心原则（不可违反）

1. **真实性 > 数量** —— Kelvin 2026-04-26 定。来源可疑直接 0 分，不进 brief。宁可 3 条也不要 8 条假的。
2. **每条必须能溯源** —— 标原始 URL，不能用「有人说」「据传」。
3. **数字 / 价格 / 时间引原文** —— 不脑补，不约等于。
4. **不确定就不写** —— 留空 / 标注「未证实」永远好过填假。

参考长期 feedback：`feedback_truth_over_volume.md`

## Step 1 · 读 sources.yaml + seen.json

项目家：`~/Desktop/Kelvin-Projects/kenyalang-ai/`

读：
- `sources.yaml` —— 来源清单（17 类，~95 个来源）
- `seen.json` —— 去重状态（每条 = URL 的 SHA256 hash，保留 90 天）

## Step 2 · 抓取（fetch）

按 `type` 字段分流：
- `web` / `rss` —— WebFetch 拿 HTML / feed
- `x_handle` —— WebFetch nitter mirror 或直接 x.com（没登入只能拿公开内容）
- `github` —— WebFetch releases 页
- `hn` —— Algolia API
- `reddit` —— `/top.json?t=day`
- `arxiv` —— RSS

按 weight 高的先抓，低的后抓。抓完每条记录：
```
{ url, title, source_name, published_at, summary_raw }
```

## Step 3 · 去重

每条 URL 算 SHA256 hash，对比 `seen.json`：
- 已见 → 丢
- 未见 → 进候选池 + 写入 `seen.json`

## Step 4 · 评分（4 道筛子）

每条候选过 4 道筛，至少 2 道过才上 brief：

1. **量级** —— frontier 级（GPT-5 / Claude 5 / Gemini 3）或行业大事（>$1B 收购、>$5B 估值）？
2. **新东西** —— 新模型 / 新能力 / 新公司，还是营销稿？
3. **Kelvin 杠杆** —— 直接帮 Fitcom 自动化 / 客户网站 / 个人工作流？
4. **行业转折** —— 影响产业格局（labs 力学、China vs US、open vs closed）？

**真实性是硬门槛 —— 来源可疑直接 0 分，不进 brief。**

按总分排序，挑 Top 5-8。其余记入「弱信号」段落。

## Step 5 · 写 brief

格式（每条 5 字段）：
- **标题** —— 一句话讲完
- **来源 + 链接** —— 谁说的（必须真实可点）
- **3 句话摘要** —— 发生了什么（不脑补）
- **含义** —— 为什么 Kelvin 要知道（一行）
- **行动建议** —— 要不要试 / 跟进 / 收藏（可选，没就不写）

末尾元数据：
```
扫描来源数：N
候选条目数：M
上 brief 数：5-8
弱信号：K
去重忽略：J
```

参考样板：`~/Desktop/Kelvin-Projects/kenyalang-ai/daily/_SAMPLE.md`

## Step 6 · 写到 daily log

文件路径：`~/Desktop/Kelvin-Projects/kenyalang-ai/daily/YYYY-MM-DD.md`

如果当天文件已存在 → 别覆盖，加 `_v2` 后缀。

## Step 7 · 发邮件（如果 Gmail 已授权）

调 Gmail MCP（`mcp__claude_ai_Gmail__send` 之类）发到 `kelvinloh@fitcomfitness.com`：
- 标题：`Kenyalang.AI · 早报 YYYY-MM-DD`
- 正文：daily/*.md 的内容（markdown 转纯文本或 HTML）

如果 Gmail 没授权 → 只写 markdown，不发邮件，告诉 Kelvin「邮件没发，授权了再补」。

## Step 8 · 周报 mode（仅周日）

如果今天是周日：
1. 读本周 7 个 daily logs
2. 抽 3 大主题
3. 写到 `weekly/YYYY-Www.md`（参考 `weekly/_SAMPLE.md`）
4. 也发邮件

---

## 用法 (Kelvin 调用)

- 每日 07:00 自动跑 → 由 `/schedule` 远程 agent 触发本 skill
- 临时跑：「跑一份今天的 AI brief」/「Kenyalang 跑一下」
- 临时调研：「最近视频生成有什么大进展」（这种就跳过 fetch all，只挑 video_gen 标签的来源跑）

## ⚠️ 不要做的事

- 不要为了凑数把推测帖、谣言、营销稿放进 brief
- 不要脑补数据 / 价格 / 时间
- 不要把弱信号美化成大新闻
- 不要写「业内人士透露」「据爆料」
- 不要在还没看到 1 手来源时就下「这是大事」的结论
