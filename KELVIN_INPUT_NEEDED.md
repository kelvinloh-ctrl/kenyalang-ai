# 还差你的输入 · Kenyalang.AI v1

---

## 已签 ✅

- ~~中文公众号清单~~ → **不追，跳过**（2026-04-26）
- ~~邮件渠道~~ → **(a) Gmail MCP 发到 kelvinloh@fitcomfitness.com**（2026-04-26）
- ~~核心原则~~ → **真实性 > 数量**（2026-04-26）

## 因此 sources.yaml 已调整

- 砍 r/singularity、r/OpenAI（谣言/粉丝向）
- Elon Musk Twitter 降权 3→2（政治噪音）
- 加 arxiv cs.AI（一手论文）
- 顶部加注释：核心原则 = 真实性 > 数量

---

## 全部已签 ✅（2026-04-27）

- ~~Q1. 行业垂直要不要加？~~ → **加 4 个 + 政府运动政策**
  - 医疗 / 法律 / 教育 / 健身 AI 全加 + sports_policy（KBS Malaysia / Sport SG / WHO / IHRSA / CDC / Sport Australia）
  - sources.yaml 升 v1.2 · 132 个来源
- ~~Q2. 第一份 brief 什么时候开跑？~~ → **立刻**
  - 第一份手动跑：`daily/2026-04-27.md` 已落地（7 条上 brief + 6 条弱信号）
  - 接下来每天 07:00 由 /schedule 远程 agent 自动跑
- ~~Q3. 要不要造一个 `kenyalang-scout` skill？~~ → **要 · 已造好**
  - skill 在 `~/.claude/skills/kenyalang-scout/`，已用本份 brief 做首跑实战验证

---

## ⚠️ 起跑 /schedule 前还差 2 件事

1. **Gmail 授权** —— 你本人点一次：`mcp__claude_ai_Gmail__authenticate`
2. **起 /schedule 远程 agent** —— 由你执行 `/schedule` 命令（这是 user-invoked，我不能代跑）

---

## 完成度

- [x] 文件夹骨架
- [x] README.md
- [x] sources.yaml v1.2（132 个来源，含 3 个新垂直）
- [x] daily/_SAMPLE.md
- [x] weekly/_SAMPLE.md
- [x] seen.json 初始化 + 11 条已记录
- [x] 中文 KOL（不追）
- [x] 邮件渠道（Gmail）
- [x] 行业垂直（医疗/法律/教育/健身 + 运动政策）
- [x] 起跑日期（立刻 · 第一份已落 daily/2026-04-27.md）
- [x] kenyalang-scout skill（已造好 + 实战验证）
- [ ] Gmail 授权（**待 Kelvin · 起 /schedule 前点一次**）
- [ ] /schedule 远程 agent 起跑（**待 Kelvin 执行 /schedule**）

---

## Backlog · 2026-05-11

### A · 修 fetcher 抽取 SPA lab 站点候选（1-2 天工程 · 待 Kelvin 选路径）

**现状**：sources.yaml 里 OpenAI / Anthropic / DeepMind / Google AI / Meta AI / xAI / Mistral / SSI / DeepSeek / Qwen / Kimi / MiniMax / Doubao / 文心 等 15+ frontier_labs + china_labs 一手源，HTTP 都 200，但 fetcher 的 `find_subpage_links()` 用 regex 抓 `<a href>` 在这些 React/Next.js SPA 站点上抓不到候选 — 因为 SPA 首页 HTML 是 shell，内容靠 JS hydration 填入。

结果：聚合站（36kr 等）每天必出多条转载 → 把官方源「卷输了」，brief 全是二手。

**B 已上线（2026-05-11）** —— 给 5 个聚合站打 `is_aggregator: true` + routine v5.3 加权重调整 + 官方优先盖聚合 + 一手源全 0 时 fallback 不拿聚合站当主菜。但这是降聚合站权重的「兜底」，不解决一手源抓不到的「治本」。

**A 治本 3 路径**（待 Kelvin 选）：

| 路径 | 做法 | 工程量 | 优劣 |
|---|---|---|---|
| **A1** | 给 fetcher 加 Playwright headless render fallback（type:web 且 stage1 home 候选 = 0 时降级 render） | ~1 天 | 最稳；增加 Playwright 依赖；render 慢 ~3-5s/源 |
| **A2** | 给每个 SPA 站手写 lxml CSS selector / XPath（OpenAI 用 `article a`、DeepMind 用 `.blog-card` 等） | ~2 天 | 不增依赖；维护成本高；站改版就坏 |
| **A3** | 把 type:web 的官方源换成它们的替代源 — GitHub Releases API / Twitter feed RSS / changelog 页面 | ~半天 | 最省事；但官方 product blog 信号比 GitHub Releases 弱；覆盖率打折 |

**Kelvin 待签**：A1 / A2 / A3 / 先观察 v5.3 跑 1 周再说
