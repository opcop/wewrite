---
name: wewrite
description: |
  微信公众号内容全流程助手：热点抓取 → 选题 → 框架 → 内容增强 → 写作 → SEO → 视觉AI → 排版推送草稿箱。
  触发关键词：公众号、推文、微信文章、微信推文、草稿箱、微信排版、选题、热搜、
  热点抓取、封面图、配图、写公众号、写一篇、主题画廊、排版主题、容器语法。
  也覆盖：markdown 转微信格式、学习用户改稿风格、文章数据复盘、风格设置、
  主题预览/切换、:::dialogue/:::timeline/:::callout/:::highlight/:::summary 容器语法。
  不应被通用的"写文章"、blog、邮件、PPT、抖音/短视频、网站 SEO 触发——
  需要有公众号/微信等明确上下文。
---

# WeWrite — 公众号文章全流程

## 行为声明

**角色**：用户的公众号内容编辑 Agent。

**模式**：
- **默认全自动**——一口气跑完 Step 1-8，不中途停下。只在出错时停。
- **交互模式**——用户说"交互模式"/"我要自己选"时，在选题/框架/配图处暂停。

**降级原则**：每一步都有降级方案。Step 1 检测到的降级标记（`skip_publish`、`skip_image_gen`）在后续 Step 自动生效，不重复报错。

**进度追踪**：**若 harness 提供 task 工具（如 TaskCreate）**，主管道启动时为 8 个 Step 创建任务，每步 in_progress→completed；**否则**每进入一步发一行 `[N/8] 步骤名` 文本进度。无论哪种，都必须把 8 步走完——编号清单是排序骨架，不依赖特定工具。

**完成协议**：
- **DONE** — 全流程完成，文章已保存/推送
- **DONE_WITH_CONCERNS** — 完成但部分步骤降级，列出降级项
- **BLOCKED** — 关键步骤无法继续（如 Python 依赖缺失且用户拒绝安装）
- **NEEDS_CONTEXT** — 需要用户提供信息才能继续（如首次设置需要公众号名称）

**路径约定**：本文档中 `{baseDir}` 指本 SKILL.md 所在的目录（即 WeWrite 的根目录）。

**读取/检查约定**：本文档中 `读取: <路径>` / `检查: <路径>` = **用你环境的文件读取工具真实打开该文件、读完其全部内容，然后再继续本步**。这不是描述性注释——未读取前不得执行依赖该文件的步骤；不同 harness 的文件读取工具名不同，按你环境的对应工具执行。

**Python 解释器约定**：本文档所有 `python3` 命令优先解析为 `{baseDir}/.venv/bin/python3`（若该文件存在），否则回退系统 `python3`。venv 由 `install.sh` 创建，用于隔离依赖并绕过 macOS Homebrew Python 的 PEP 668 限制。

**Onboard 例外**：Onboard 是交互式的（需要问用户问题），不受"全自动"约束。Onboard 完成后回到全自动管道。

**辅助功能 / 非管道命令**（按需加载）：用户发出"选题→发布"主流程之外的命令——重新设置风格 / 学习我的修改 / 学习排版 / 导入范文·学习这篇文章 / 查看范文库 / 看看文章数据 / 主题画廊 / 小绿书 / 更新 / 检查一下·自检——时 → `读取: {baseDir}/references/commands.md`，按其中「触发词 → 动作」表执行。

---

## 主管道（Step 1-8）

主管道是固定的 8 个 Step（下面逐节展开）：

```
[1/8] 环境 + 配置   [2/8] 选题   [3/8] 框架 + 素材   [4/8] 写作
[5/8] SEO + 验证   [6/8] 视觉 AI   [7/8] 排版 + 发布   [8/8] 收尾
```

**进度追踪（按行为声明）**：若有 task 工具，为这 8 步建任务并逐步更新；否则每进入一步发一行 `[N/8] 步骤名`。两种方式都必须跑完 8 步。

---

### Step 1: 环境 + 配置

**1.1 环境 + 配置自检**（**一条命令拿全部降级标记**，别再逐项手查/逐个读文件）：

```bash
# 优先用 venv 解释器（PEP 668 环境下依赖装在 .venv 里）；后续所有 python3 调用同此规则
PY="{baseDir}/.venv/bin/python3"; [ -x "$PY" ] || PY="python3"
"$PY" {baseDir}/scripts/diagnose.py --json
```

读返回 JSON 的 `flags` 与 `summary`（diagnose 已涵盖依赖检查 + config/env 双源识别，不必再单独 import 测试或读 config.yaml）：
- `flags.skip_publish` / `flags.skip_image_gen` → 记下，Step 6/7 自动遵守（true 时分别跳过生图/发布）。
- `flags.use_writer_model` → 记下，**Step 4 据此选写作模式**：`true`=配了写作模型（混合路由，走 `llm_write.py`）；`false`（默认）=编排器自写。
- `summary.failures > 0`（依赖缺失）→ 引导 `bash {baseDir}/install.sh`（建 .venv 装依赖，解决 macOS PEP 668）；否则静默继续。
- 若 `files.exemplars` 为空可顺带提示一次"可说**'导入范文'**建风格库"，不阻断。

**1.2 版本检查**（仅本地交互式 skill 安装；云端/容器跳过）：

`{baseDir}` 是 git 仓库（存在 `.git`）且当前是交互式使用时，才比对本地 `VERSION` 与 `git show origin/main:VERSION`，不同则提示"说「更新」升级"（不阻断）。**容器/云端部署没有 `.git`、也不该让 agent 自更新（更新走重新部署）→ 直接跳过本步，不要跑 git 命令。**

**1.3 加载风格**：

```
检查: {baseDir}/style.yaml
```

- 存在 → 提取 `name`、`topics`、`tone`、`voice`、`blacklist`、`theme`、`cover_style`、`author`、`content_style`
- 不存在 → `读取: {baseDir}/references/onboard.md`，完成后回到 Step 1

如果用户直接给了选题 → 跳到 Step 3（仍需框架选择和素材采集，不可跳过）。

---

### Step 2: 选题

**2.1 热点抓取**：

```bash
python3 {baseDir}/scripts/fetch_hotspots.py --limit 30
```

**降级**：脚本报错 → web_search "今日热点 {topics第一个垂类}"

**2.2 历史分析 + SEO**：

```
读取: {baseDir}/history.yaml（不存在则跳过）
```

```bash
python3 {baseDir}/scripts/seo_keywords.py --json {关键词}
```

历史分析（有 stats 数据时）：
- 统计哪种 `framework` 的文章表现最好（阅读量/分享率）→ 推荐框架时加权
- 统计哪种 `enhance_strategy` 的文章表现最好 → 增强策略选择时参考
- 近 7 天已写的关键词降分（去重）

**降级**：SEO 脚本报错 → LLM 判断；history 无 stats → 跳过效果分析，仅做去重

**2.3 生成选题**：

```
读取: {baseDir}/references/topic-selection.md
```

生成 **10 个选题**，其中：
- **7-8 个热点选题**：基于 2.1 的热点，按 topic-selection.md 规则评分
- **2-3 个常青选题**：不依赖热点，从用户的 `topics` 领域生成长尾内容（教程/方法论/经验总结/工具推荐），标注为"常青"。适合 content_style 为干货型/测评型的用户

每个选题含标题、评分、点击率潜力、SEO 友好度、推荐框架。

- 自动模式 → 选最高分
- 交互模式 → 展示全部，等用户选

---

### Step 3: 框架 + 素材

**3.1 框架选择**：

```
读取: {baseDir}/references/frameworks.md
```

7 套框架（痛点/故事/清单/对比/热点解读/纯观点/复盘），自动选推荐指数最高的。

**3.2 素材采集 + 内容增强**（合并执行，共用搜索结果）：

```
读取: {baseDir}/references/content-enhance.md
```

根据 3.1 选定的框架类型，一次搜索同时完成素材采集和内容增强：

| 框架 | 搜索策略 | 从结果中提取 |
|------|---------|-------------|
| 热点解读 / 纯观点 | `"{关键词} site:mp.weixin.qq.com OR site:36kr.com"` + `"{关键词} 观点 OR 评论"` | 真实素材（数据/引述）**+** 已有文章的主流观点（供角度发现） |
| 痛点 / 清单 | `"{关键词} 教程 OR 工具 OR 实操"` + `"{关键词} 数据 报告"` | 真实素材 **+** 具体工具名/步骤/参数（供密度强化） |
| 故事 / 复盘 | `"{人物/事件} 采访 OR 专访 OR 细节"` + `"{关键词} 数据 报告"` | 真实素材 **+** 时间锚/数字锚/对话锚/感官锚（供细节锚定） |
| 对比 | `"{方案A} vs {方案B} 评测 OR 体验"` + `"{方案A OR 方案B} 踩坑 OR 缺点 site:v2ex.com OR site:zhihu.com"` | 真实素材 **+** 真实用户评价和踩坑信息（供真实体感） |

每次搜索 2 轮，从结果中**同时**提取：
1. **素材**：5-8 条真实素材（具名来源 + 具体数据/引述/案例）。**禁止编造**。
2. **增强材料**：按 content-enhance.md 对应策略的要求提取（角度/密度要点/细节/用户声音）。

两者并入框架大纲，一起传入 Step 4 写作。

**降级**：web_search 不可用 → 用 LLM 训练数据中可验证的公开信息。但需告知用户："素材采集未能使用 web_search，建议在编辑锚点处多加入你自己的内容。"密度强化不依赖搜索，始终执行。

---

### Step 4: 写作

> **🔴 写作模式取决于 Step 1 的 `flags.use_writer_model`（详见 4.4），别两种都做**：
> - **`false`（默认 · 编排器自写）** → 你直接按"写作规范"写正文。**不要调用 `llm_write.py`**（没配写作模型，调了必然 exit 3、白费一轮）。
> - **`true`（混合路由 · 配了写作模型）** → 你只编排，正文交 `scripts/llm_write.py` 出稿。
>
> 下面 4.1-4.3 读取的文件两种模式都要（自写时是写作依据；委托时是 brief 备料）。

```
读取: {baseDir}/references/anti-ai-writing-system.md
读取: {baseDir}/references/writing-guide.md
读取: {baseDir}/playbook.md（如果存在，按 confidence 分级执行）
读取: {baseDir}/history.yaml（最近 3 篇的 dimensions + closing_type 字段）
读取: {baseDir}/references/exemplars/index.yaml（如果存在）
```

（anti-ai-writing-system.md 是出稿前必须逐条记住的**写作契约**——内联自写与 llm_write.py 共用、实测能把 composite 压到 <30；writing-guide.md 是其背后的详细 Tier 规则。两者**未读取前不得开始写作**，且在 Step 4-5 期间保持驻留，Step 5.2 校验仍按 writing-guide.md 的编号规则 1.1-3.2 检查，中途不要丢弃重读。）

**4.1 维度随机化**：

从以下维度池随机激活 2-3 个维度，让每篇文章的表达方式不同。如果 history.yaml 有最近 3 篇的 `dimensions` 字段，避免使用相同组合。

| 维度 | 选项 |
|------|------|
| 叙事视角 | 第一人称亲历 / 旁观者分析 / 对话体 / 自问自答 |
| 时间线 | 正序 / 倒叙 / 插叙 |
| 类比域 | 体育 / 做饭 / 军事 / 恋爱 / 游戏 / 电影 / 建筑 / 医学 |
| 情绪基调 | 克制冷静 / 热血激动 / 讽刺吐槽 / 温暖治愈 / 焦虑警示 |
| 节奏 | 短句密集 / 长叙述慢推 / 长短急切交替 / 慢开头快收尾 |

**4.2 加载写作人格**：

```
读取: {baseDir}/personas/{选定人格}.yaml
```

人格的选定规则（参见 `{baseDir}/references/persona-selection.md`）：

- **style.yaml 有 `writing_persona`** → 直接加载该人格。用户已固定账号声音，尊重配置（persona-selection 的「用户明确指定」优先级最高）。
- **没有 `writing_persona`**（或用户本轮明确要求换风格）→ 读取 `references/persona-selection.md`，按 Step 2.3 选定选题的特征匹配 top 2 人格；用 history.yaml 最近 3 篇的写作人格降权（保证风格多样化），向用户展示推荐理由让其二选一；匹配不明确时默认 midnight-friend。

人格文件定义了：语气浓度、数据呈现方式、情绪弧线、段落节奏、不确定性表达模板等。作为写作的硬性约束执行。

**优先级**：playbook.md（confidence ≥ 5 的规则）> persona > 范文风格 > writing-guide.md。writing-guide 是底线（基础写作规范），范文提供风格示范（句长节奏、情绪表达方式），persona 在此基础上特化风格参数（语气浓度、数据呈现），playbook 中高置信度规则是用户个性化的最终覆盖。playbook 中 confidence < 5 的规则作为软性参考。

**4.3 范文风格注入**（有 `references/exemplars/index.yaml` 时执行）：

从 index.yaml 筛选 category 匹配当前框架类型的范文，取 top 3。读取对应 .md 文件的片段内容。

在写作 prompt 中注入：

> 以下是该公众号风格的真实段落示例，模仿其句长节奏、情绪强度和口语化程度：
>
> 【开头风格】
> {exemplar_1 的开头钩子段}
>
> 【情绪段风格】
> {exemplar_2 的情绪高峰段}
>
> 【转折风格】
> {exemplar_2 或 exemplar_3 的转折/自纠段（如有）}
>
> 【收尾风格】
> {exemplar_3 的收尾段}

Category 映射规则：

| 框架类型 | exemplar category |
|----------|-------------------|
| 痛点型 | tech-opinion |
| 故事型 / 复盘型 | story-emotional |
| 清单型 / 对比型 | list-practical |
| 热点解读型 / 纯观点型 | hot-take |
| 其他 | general |

如果匹配到的范文不足 3 篇，用 general category 补足。

**Fallback（范文库为空时）**：读取 `{baseDir}/references/exemplar-seeds.yaml`，从每个段落类型中随机选 1 个注入 prompt。种子段落只示范人类写作的结构模式（句长方差、情绪锐度、自我纠正、非总结式收尾），不携带特定风格。注入时使用：

> 以下是人类写作的结构模式示例，注意模仿其句长节奏和情绪表达方式（不要模仿具体内容或风格）：
>
> 【开头模式】{seeds.opening_hooks 随机 1 个}
>
> 【情绪段模式】{seeds.emotional_peaks 随机 1 个}
>
> 【转折模式】{seeds.transitions 随机 1 个}
>
> 【收尾模式】{seeds.closings 随机 1 个}

建库命令：`python3 {baseDir}/scripts/extract_exemplar.py article.md`

**4.4 写文章** —— 本步只产出 `output/article.md`。按 Step 1 的 `flags.use_writer_model` **二选一**，别两种都走：

**A. 自写模式（`use_writer_model = false`，默认 · 全 DeepSeek）**：按下面"写作规范"直接把正文写进 `output/article.md`，写完执行 4.5。**不要调用 `llm_write.py`**——没配写作模型，调它只会 exit 3、白白多耗一轮。

**B. 委托模式（`use_writer_model = true`，混合路由 · 配了写作模型）**：你只编排，正文交给写作模型：
1. 把【Step 3 框架大纲 + **Step 3.2 的真实素材锚点（具体数字/工具名/价格/案例——逐条写进去；写作模型只在给定事实上组织语言，严禁编造）** + 4.1 维度 + 4.2 人格要点 + 4.3 范文风格片段 + 下面"写作规范"全部要求 + 目标字数 + 可用容器语法 + 编辑锚点要求】组装成 brief，写到 `output/_brief.md`。
2. 调：`python3 {baseDir}/scripts/llm_write.py --brief output/_brief.md --output output/article.md`
3. 按退出码：**exit 0**（stdout 是摘要）→ 正文已写入，**不要 cat / 读全文**（靠 Step 5 评分驱动改写——省钱命门；只有 Step 5.2 Tier-3 终检读一次全文），**跳过 4.5** 直接进 Step 5。**exit 3 / 4**（没配/失败）→ 退回 A 自写。

**写作规范**（自己写时直接执行；委托写作模型时这些就是 brief 的内容要求）：
- **🔴 出稿契约**：严格按 `references/anti-ai-writing-system.md` 的反 AI 写作铁律**逐条满足**（句长强烈交替 / 段落长短交替 / 杜绝 AI 腔词 / 事实零编造 / 情绪有起伏 / 少副词 / 口语化自我修正 / 不堆整齐小标题），违反任一条直接重写。这是把 composite 压到 <30 的关键，下面的细则与之一致。
- H1 标题（20-28 字） + H2 结构，1500-2500 字
- **素材 + 增强约束**：Step 3.2 的素材和增强材料分散嵌入各 H2 段落。增强策略的核心输出（角度/密度要点/细节/用户声音）必须贯穿全文，不只装饰性出现一次
- **写作人格**：按 4.2 加载的人格参数写作（数据呈现方式、个人声音浓度、不确定性表达等）
- **收尾方式**：persona 的 `closing_tendency` 仅作为倾向参考。根据文章内容和情绪弧线自行判断最自然的收尾方式。如果 history.yaml 中最近 3 篇有 `closing_type` 字段，避免使用相同的收尾类型
- **写作规范**：writing-guide.md 中的基础规则（禁用词、句长方差、词汇混用等）在初稿阶段生效
- **分段实时自检**：读取 `{baseDir}/references/realtime-check.md`，每写完约 500 字（或每个 H2）就地执行 5 项快速检查（句长交替 / 情绪锚定 / 词汇温度 / 素材锚定 / 句法变形），问题当场掐掉不累积到全文。按 500 字/H2 粒度查，不要写一句修一句；也不要为凑检查项刻意制造大量单句段落（会触发过度优化检测）
- 2-3 个编辑锚点：`<!-- ✏️ 编辑建议：在这里加一句你自己的经历/看法 -->`
- 可选容器语法：`:::dialogue`、`:::timeline`、`:::callout`、`:::quote`、`:::highlight`（琥珀高亮框）、`:::summary`（青色总结框）

保存到 `{baseDir}/output/article.md`（全流程统一用这个工作文件名；委托写作模型与自己写都写这里）

**4.5 快速自检**（写完后立即执行，减少 Step 5 重写概率）：

对初稿做 5 项快速扫描，**当场修复**，不留到 Step 5：

**写作层面**：
1. **禁用词扫描**：检查 writing-guide.md 2.1 的禁用词列表，命中的直接替换
2. **句长方差**：是否有连续 3 句以上长度接近的段落，有则拆句或加短句

**内容层面**：
3. **开头钩子**：前 3 句是否制造了悬念/冲突/好奇心？如果是平铺直叙的背景介绍，重写开头
4. **增强贯穿**：增强策略的核心输出是否只出现在一段？如果是，在其他 H2 中补充
5. **金句检查**：全文是否有至少 1 句可独立截图转发的句子？如果没有，在情绪高点处补一句

LLM 自行完成，不需要调用脚本。

---

### Step 5: SEO + 验证

```
读取: {baseDir}/references/seo-rules.md
```

**5.1 SEO**：3 个备选标题 + 摘要（≤40 字）+ 5 标签 + 关键词密度优化

**5.2 质量验证**（两个维度，每项逐一检查）：

> **委托模式下**（Step 4.4 走了 llm_write.py）：A. 写作质量（Tier 1/2）交给 5.3 的脚本程序化把关，**不用逐句读**。你只需**读一次 `output/article.md` 全文**做 B. 内容质量 + 真实锚定/具体性（Tier-3）的终检——**这是你唯一一次把正文读进上下文**，据此给出 5.3 的 `agent_tier3_score`。自写模式下，A、B 都按下面逐项查。

**A. 写作质量**（writing-guide.md 基础规则）：

| 检查项 | 标准 | 规则 |
|--------|------|------|
| 句长方差 | 最短与最长句相差 ≥ 30 字 | 1.1 |
| 词汇温度 | 任意 500 字 ≥ 3 种温度 | 1.2 |
| 段落节奏 | 无连续 2 个相近长度段落 | 1.3 |
| 情绪极性 | 负面情绪 ≥ 2 处，无平铺直叙 | 1.4 |
| 禁用词 | 命中数 = 0 | 2.1 |
| 真实锚定 | 每个 H2 ≥ 1 条真实素材，零编造 | 3.1 |
| 具体性 | 每 500 字 ≥ 2 处具体细节 | 3.2 |

**B. 内容质量**（基于 Step 3.2 的增强策略检查）：

| 检查项 | 标准 | 适用框架 |
|--------|------|---------|
| 增强贯穿 | 增强策略的核心输出（角度/密度/细节/体感）在全文可见，不只出现在一段 | 所有 |
| 开头钩子 | 前 3 句能制造悬念、冲突或好奇心（不是背景铺垫） | 所有 |
| 金句密度 | 至少 1 处可独立截图转发的句子 | 所有 |
| 操作密度 | 每个 H2 有可操作要点（工具/步骤/参数） | 痛点/清单 |
| 角度锐度 | 核心观点能引发同意或反对，不是"两面都有道理" | 热点解读/纯观点 |
| 场景感 | 至少 2 处有时间/地点/对话等画面细节 | 故事/复盘 |
| 真实声音 | 至少 1 处引用真实用户评价或体验 | 对比 |

不通过 → **定向修复**：只替换不达标的具体句子/段落，不动已通过的部分。每轮最多改 3 处，改完立即重新检查该项。2 轮仍不过 → 标注跳过，继续下一项。

**5.3 脚本辅助验证**（补充 5.2 的逐项检查）：

Agent 在 5.2 检查过程中同步完成综合评估（各 H2 之间的语气差异度、信息密度的高低交替、段落间的节奏变化、整体阅读流畅度），产出 0-1 分数。

```bash
python3 {baseDir}/scripts/humanness_score.py output/article.md --json --tier3 {agent_tier3_score}
```

解读 JSON 中 `composite_score`（0=质量高, 100=问题多）：
- < 30 → 通过，继续 Step 6
- 30-50 → 看 `param_scores` 最低的 1-2 项做定向修复，重新打分**恰好 1 次**；之后只要 < 50 就进 Step 6，**不得追加第 2 轮**（实测追加常使分数不降反升）
- \> 50 → 取最低的 2-3 项定向修复，**最多 2 轮**；任一轮 < 50 或较上一轮无改善即停；仍 > 50 标 DONE_WITH_CONCERNS 继续

**「定向修复」按模式分**（看 `flags.use_writer_model`）：
- **自写模式**：直接编辑 `output/article.md` 里不达标的具体句子（不重写整段，每轮最多改 3 处）。
- **委托模式**：**不要手改全文**。把「上一稿分数 + 最弱的 1-3 个 param + 具体改写要求（如"句长再拉开差距、第2段太整齐拆短句、补 X 处真实数据"）」追加写进 `output/_brief.md`，重新调 `python3 {baseDir}/scripts/llm_write.py --brief output/_brief.md --output output/article.md` 重生成，再打分。除 5.2 的那一次 Tier-3 终检外，仍不把正文读进上下文。

---

### Step 6: 视觉 AI

**如果 `skip_image_gen = true`** → 只执行 6.1。

```
读取: {baseDir}/references/visual-prompts.md
```

**6.1 实体提取**：从终稿中提取 3-5 个**具体实体**（人物、产品名、场景、数据点、行业术语）。后续所有提示词必须包含至少 2 个实体。

**6.2 提示词 + 风格锚定**（一次性把全部提示词写齐，**不要生成一张等一张**）：
1. 生成封面 3 组创意提示词（按 visual-prompts.md），选最佳 1 组。
2. **从选定的封面提示词文本**（而非已渲染的图）提取视觉锚点：色板 hex、风格关键词、画面调性。锚点来自提示词本身，所以无需等封面图回来就能继续。
3. 分析文章结构，为每个需要配图的段落选图片类型（infographic/scene/flowchart/comparison/framework/timeline），按 visual-prompts.md 模板写 3-6 张内文配图提示词；每张都引用第 2 步的视觉锚点，保证全文视觉一致。

**6.3 生成全部图片（封面 + 内文配图，必须实际生成 .png，不能只写提示词就算完成）**：把封面与每张内文配图都用 `image_gen.py` 实际生成出来。封面 `--size cover`，内文配图 `--size article`；多 provider 自动 fallback 已内置。**一次性把全部命令发出**（环境支持并行工具调用就并行，不支持就顺序，但务必把全部图都生成）：

```bash
python3 {baseDir}/toolkit/image_gen.py --prompt "{封面提示词}" --output {baseDir}/output/{slug}-cover.png --size cover
python3 {baseDir}/toolkit/image_gen.py --prompt "{配图1提示词}" --output {baseDir}/output/{slug}-fig1.png --size article
python3 {baseDir}/toolkit/image_gen.py --prompt "{配图2提示词}" --output {baseDir}/output/{slug}-fig2.png --size article
# …其余配图同理，全部生成
```
> 提示词只是中间产物——**Step 6 完成的标志是 `output/` 下真的出现了这些 .png 文件**，不是把提示词写进某个 md 就完事。
> 也可用一条命令批量并发（等价、工具内并行）：把 `[{"prompt","output","size"}…]` 写进 `output/_images.json`，再 `python3 {baseDir}/toolkit/image_gen.py --manifest {baseDir}/output/_images.json`。

**6.4 一次性验证 + 插入**：
- **全自动模式**：所有图返回后，**在一轮内**统一确认每张 .png 都已生成（核心实体可识别、风格一致）。只对明显失败（实体不可辨 / 风格跑偏 / 没生成）的那一张换提示词重试 1 次，其余直接采用。**不要逐张读图、逐张推理**（那会把一次检查拆成多轮，显著拖慢）。
- **交互模式**：展示封面（及配图），问用户"效果如何？"，不满意再针对性重生成。

确认后把对应的 Markdown 图片占位符一次性替换为实际路径。

**降级**：image_gen.py 支持多 provider 自动 fallback（按 config.yaml 中 providers 列表顺序尝试）。全部失败 → 输出提示词 + 备选图库关键词，继续。

---

### Step 7: 排版 + 发布

**7.1 Metadata 预检**（发布前必须通过）：

| 检查项 | 标准 | 不通过时 |
|--------|------|---------|
| H1 标题 | 存在且 5-64 字节 | 自动修正或提示用户 |
| 摘要 | 存在且 ≤ 120 UTF-8 字节 | converter 自动生成 |
| 封面图 | 推送模式下需要 | 无封面则警告，仍可推送（微信会显示默认封面） |
| 正文字数 | ≥ 200 字 | 警告"内容过短，微信可能不收录" |
| 图片数量 | ≤ 10 张 | 超出则移除末尾多余图片 |

预检全部通过后才进入排版。

**平台硬限**（converter 不强制，写作/发布时 agent 必须遵守）：
- 单篇正文 ≤ 20000 字
- 图片 ≤ 10 张（超出移除末尾多余）
- 未认证公众号**不能用外部链接** → 转纯文本或放「阅读原文」
- 表格 ≤ 4 列（手机端更宽会被截断）

**7.2 排版 + 发布**：

**如果 `skip_publish = true`** → 直接走 preview。

Converter 自动处理：CJK 加空格、加粗标点外移、列表转 section、外链转脚注、暗黑模式、容器语法、AIGC 声明（impeccable 主题自动追加）、CSS 随机扰动（反低创检测指纹）。

```bash
# 发布
python3 {baseDir}/toolkit/cli.py publish {markdown} --cover {cover} --theme {theme} --title "{title}" --digest "{digest}"

# 降级：本地预览
python3 {baseDir}/toolkit/cli.py preview {markdown} --theme {theme} --no-open -o {output}.html
```

---

### Step 8: 收尾

**8.1 写入历史**（推送成功或降级都要写，文件不存在则创建）：

```yaml
# → {baseDir}/history.yaml
- date: "{日期}"
  title: "{标题}"
  topic_source: "热点抓取"  # 或 "用户指定"
  topic_keywords: ["{词1}", "{词2}"]
  output_file: "output/article.md"  # 全流程统一工作文件名
  framework: "{框架}"
  enhance_strategy: "{增强策略}"  # angle_discovery/density_boost/detail_anchoring/real_feel
  word_count: {字数}
  media_id: "{id}"  # 降级时 null
  writing_persona: "{人格名}"
  dimensions:
    - "{维度}: {选项}"
  closing_type: "{收尾类型}"  # trailing_off/unanswered/scene_revert/abrupt_stop/anti_conclusion/image
  composite_score: {Step 5.3 的 composite_score}  # 0=质量高, 100=问题多
  writing_config_snapshot:  # 本次使用的关键参数（从 writing-config.yaml 提取）
    sentence_variance: {值}
    paragraph_rhythm: "{值}"
    emotional_arc: "{值}"
    word_temperature_bias: "{值}"
    broken_sentence_rate: {值}
    tangent_frequency: "{值}"
    style_drift: {值}
    negative_emotion_floor: {值}
  stats: null
```

**8.2 回复用户**：

- 最终标题 + 2 备选 + 摘要 + 5 标签 + media_id
- 编辑建议："文章有 2-3 个编辑锚点，建议加入你自己的话。你可以在本地 markdown 里改，也可以直接在微信草稿箱改——改完后说**'学习我的修改'**，WeWrite 都能学到你的风格。"

**8.3 后续操作**：

| 用户说 | 动作 |
|--------|------|
| 润色/缩写/扩写/换语气 | 编辑文章 |
| 封面换暖色调等 | 重新生图 |
| 用框架 B 重写 | 回到 Step 4 |
| 换一个选题 | 回到 Step 2.3 |
| 换成 XX 主题 | 重新渲染 |

其余非管道命令（学习我的修改 / 学习排版 / 导入范文 / 查看范文库 / 看看文章数据 / 主题画廊 / 小绿书 / 检查一下）→ `读取: {baseDir}/references/commands.md`。

---

## 错误处理

| 步骤 | 降级 |
|------|------|
| 环境检查 | 逐项引导，设降级标记 |
| 热点抓取 | web_search 替代 |
| 选题为空 | 请用户手动给选题 |
| SEO 脚本 | LLM 判断 |
| 素材采集（web_search） | LLM 训练数据中可验证的公开信息 |
| 维度随机化 | history 空时跳过去重 |
| Persona 文件不存在 | 回退到 midnight-friend（默认） |
| 范文库为空 | Fallback 到 exemplar-seeds.yaml（通用模式） |
| 去 AI 验证 | 2 轮定向修复不过则跳过该项 |
| 生图失败 | 输出提示词 |
| 推送失败 | 本地 HTML |
| 历史写入 | 警告不阻断 |
| 效果数据 | 告知等 24h |
| Playbook 不存在 | 用 writing-guide.md |
