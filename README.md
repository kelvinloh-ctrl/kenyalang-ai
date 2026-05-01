# Kenyalang.AI · 全球 AI 产业情报 Agent

> **犀鸟 = Hornbill = 视野最远的鸟**
> 替 Kelvin 看全球 AI 产业，每天早 7 点带回最该关注的 5-8 条。

---

## 这个 Agent 服务谁

- **主人**：Kelvin（个人）
- **二级受益**：Kelvin 用情报喂 Fitcom 决策 + 客户咨询
- **不服务**：直接喂给 Fitcom（那是 Kenyalang.Fit 的活，未来项目）

## 它做什么 / 不做什么

**做**：
- 扫全球 AI 产业新闻（labs / 工具 / 模型 / 收购 / 人事 / 融资）
- 每日早 brief → 邮件 + log
- 每周 digest → 邮件 + log
- 按需 Q&A（Kelvin 问就答，读 log + 实时搜）

**不做**：
- 不做健身行业情报（那是 Kenyalang.Fit）
- 不主动推送非 AI 内容
- 不做投资建议（只报事实 + 含义）

---

## 架构（v1）

```
[sources.yaml]
     │
     ▼
┌─────────────────────────────┐
│ Daily Scout · 每日 07:00    │  ← /schedule 远程 agent
│ 1. fetch all sources        │
│ 2. dedupe vs seen.json      │
│ 3. rank → top 5-8           │
│ 4. Claude 摘要 + 含义        │
└─────────────────────────────┘
     │
     ├──→ 邮件 → kelvinloh@fitcomfitness.com
     └──→ 日志 → daily/YYYY-MM-DD.md

┌─────────────────────────────┐
│ Weekly Digest · 周日 19:00  │  ← /schedule 远程 agent
│ 1. 读本周 7 个 daily logs   │
│ 2. 抽主题 + 趋势            │
│ 3. 写「这周值得关注」       │
└─────────────────────────────┘
     │
     ├──→ 邮件 → kelvinloh@fitcomfitness.com
     └──→ 日志 → weekly/YYYY-Www.md

[Q&A · 随时] Kelvin 问 Claude → 读 logs + 实时 web 搜
```

## 文件结构

```
kenyalang-ai/
├── README.md              ← 本文件（架构 + 操作手册）
├── sources.yaml           ← 来源清单（YAML，可直接编辑）
├── seen.json              ← 去重状态（自动维护，别手改）
├── daily/                 ← 每日 brief log
│   └── _SAMPLE.md         ← 样本格式
├── weekly/                ← 每周 digest log
│   └── _SAMPLE.md
├── _archive/              ← 旧 logs 归档（>90 天）
└── KELVIN_INPUT_NEEDED.md ← 还差你给的输入
```

## 简报评分原则（哪条值得报）

每条候选过 4 道筛子，至少 2 道过才上 brief：

1. **量级** —— 是不是 frontier 级别（GPT-5 / Claude 5 / Gemini 3）或行业大事（>$1B 收购、>$5B 估值）？
2. **新东西** —— 是新模型、新能力、新公司，还是只是营销？
3. **Kelvin 杠杆** —— 能直接帮 Fitcom 自动化 / 客户网站 / 个人工作流吗？
4. **行业转折** —— 影响产业格局（labs 之间力学、China vs US、open vs closed）？

## 邮件 brief 格式（每日）

每条 5 个字段：
- **标题** —— 一句话讲完
- **来源 + 链接** —— 谁说的
- **3 句话摘要** —— 发生了什么
- **含义** —— 为什么 Kelvin 要知道（一行）
- **行动建议** —— 要不要试 / 跟进 / 收藏（可选）

## 周报 digest 格式

- **本周 3 大主题** —— 抽象出趋势
- **每个主题 2-3 条支撑事件**
- **Kelvin 的杠杆点** —— 这周冒出的可用工具 / 可学的概念
- **下周值得盯** —— 预告

---

## 操作（v1 跑起来后）

```bash
# 改来源清单
vim sources.yaml

# 看今天 brief（如果你忘了看邮件）
cat daily/$(date +%Y-%m-%d).md

# 看本周 digest
ls -lt weekly/ | head -5
```

## 状态

- v1 架构骨架：✅ 落地（2026-04-26）
- sources.yaml v1：✅ 落地
- /schedule 远程 agent：⏳ 待 Kelvin 签字开
- 邮件发送：⏳ 待 Kelvin 签字开
- 第一份 brief：⏳ 待 Kelvin 签字开

## 决策日志

- **2026-04-26** Kenyalang 拆 2 模块：`.AI`（今天做）+ `.Fit`（未来做，原 2026-03-29 决策）
- **2026-04-26** 服务对象 = Kelvin 个人；频率 = 每日 brief + 每周 digest + 按需 Q&A；范围 = 全网扫
- **2026-04-26** 架构选 A：/schedule 远程 agent（不走 n8n / launchd）
