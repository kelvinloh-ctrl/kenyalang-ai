# Kenyalang.AI · 周度宏观研判 routine（Track B）

- 建立：2026-06-17 · ADR: `~/Desktop/Kelvin_SecondBrain/Journal/Decisions/Archive/2026-06-17-kenyalang-intel-system-redesign.md`
- 跑频：周日晚 MYT（计划接 RemoteTrigger cron · 先手动跑验证）
- 角色：方向 3 的「研判 agent」—— 抓取(fetcher)管离散事件，本 routine 管**趋势综合 + 持仓快照**
- 引擎：WebSearch + WebFetch（不依赖 Mac fetcher · 这些源多数 fetcher 403/202 抓不到）

## 铁律（最高优先 · 守「真实性 > 数量」）

1. **判断可以综合，数字必须溯源。** 每一个数字（点位/利率/CPI/汇率/股价）后面必须挂 **来源 URL + as-of 日期**。
2. **核查兜底。** 同一数字尽量两源对照；对不上 / 找不到源 → **标 TBD 删掉，不写**。宁缺毋滥。
3. **禁编造、禁脑补、禁用记忆里的旧数字。** 全部当场 WebSearch/WebFetch 取。
4. **旧数据如实标旧。** 抓到的是上周/上月的就写 as-of 那天，不冒充「今天」。
5. 代码核对：报马股前核对 Bursa 代码（先例：Oriental Kopi 是 **0338** 非 5302）。

## 输出

写 `weekly/{周日 MYT 日期}-macro.md`，4 段：

### 1. 经济走向 · 马来西亚 vs 世界
- **大马**：BNM OPR 利率立场（MPC 最近一次）· DOSM 最新 CPI / GDP / 失业 / 贸易 · 财政/投资（MOF/MIDA 有重大才提）
- **世界**：美联储 FOMC 立场 + 点阵图方向 · ECB · IMF/World Bank/OECD 旗舰报告（有就提）· 油价 · 美元指数
- **综合判断**：MY 往哪走 vs 世界往哪走（2-4 句·基于上面数字·不空谈）
- **对 Kelvin 的含义**：Fitcom 成本（利率/通胀/最低工资）· 进口器材（USD/MYR）· 持仓

### 2. 持仓快照（每周收盘）
表格：6 只 + 涨跌 + 离 52 周高/低 + 近期除息。源焊死、逐条标 as-of。
- 马股 5 只：Maybank(1155) · CIMB(1023) · YTL Power(6742) · Mr DIY(5296) · Oriental Kopi(**0338**·KOPI)
- 美股：**VOO**（Vanguard S&P500）+ 当日 USD/MYR（VOO 入场成本 = 价 × 汇率）
- **报价源优先级**（实测稳）：Google Finance(`代码:KLSE`，大盘准) → isaham.my / i3investor / stockanalysis(KLSE:TICKER) / malaysiastock.biz。⚠️ 避免 Yahoo `代码.KL`（实测把 0338 抓成别家公司）。

### 3. 本周/下周数据日历
列即将发布的：BNM MPC 会议日 · DOSM 发布日历(CPI/GDP) · FOMC 会议日 · 重大 IPO 申购窗口。让 Kelvin 知道何时有大数据。

### 4. 估值温度计（VOO/S&P500）
CAPE + 前瞻 P/E + 现价 vs 50/200 日均线 + 分析师目标区间 → 一句「贵/中/便宜」。**不报买入价**（Kelvin 自己决策）。

## 源清单（research_only · 见 sources.yaml macro 桶）

| 源 | 用途 | 抓法 |
|---|---|---|
| Fed `press_monetary.xml` | FOMC 立场 | fetcher 已抓(RSS) / 本 routine 复核 |
| ECB / World Bank | 欧央行 / 多边 | fetcher 抓子页 / 本 routine 复核 |
| BNM | MY 利率(MPC 6次/年) | WebSearch（fetcher 202）|
| IMF / OECD | WEO / Economic Outlook | WebSearch（fetcher 403）|
| OpenDOSM `open.dosm.gov.my` + API `developer.data.gov.my/static-api/opendosm` | MY GDP/CPI/失业/贸易 | WebFetch release 页（无 RSS）|
| MOF / MIDA | MY 财政 / FDI | WebSearch（不定期）|

## 报告结尾
明确说：「Track B 周度研判完成 · 走向 X 段 · 持仓 6 只(实时 N / 旧 M) · 数字全溯源 · 写入 weekly/{date}-macro.md」。
