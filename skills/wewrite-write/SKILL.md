---
name: wewrite-write
description: |
  WeWrite 写作模块：在公众号选题明确后完成框架、素材和正文。由主流程调用，或响应
  “就这个选题写正文”。通用写作、博客和短视频文案不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - WebSearch
  - WebFetch
---

# wewrite-write — 框架、素材、正文

## 前置

运行 `wewrite run show` 读取当前任务。没有任务但用户给了选题时，先以 `draft` 模式
创建；没有选题则转 `wewrite-topic`。正文只写到 `artifacts.article` 指向的文件。

读取 `{home}/style.yaml`；不存在则先执行 `wewrite-style`。按优先级读取自定义人格
`{home}/personas/<name>.yaml`、内置 `personas/<name>.yaml`，最后回退 `midnight-friend`。

进入时运行：

```bash
wewrite run step write in_progress
```

## 3. 框架与素材

完整读取：

```text
读取: {skill_dir}/references/editorial-quality.md
读取: {skill_dir}/references/frameworks-quick.md
```

从痛点、故事、清单、对比、热点解读、观点、复盘中选最适合的一种，不为变化而变化。

围绕文章真正需要证明的 3-6 个主张搜索。每条进入文章的具体数据、引述、案例或时效性
事实，都必须在搜索结果页面中核对，并立刻记录：

```bash
wewrite sources add --url "{原始页面}" --title "{标题}" --publisher "{发布方}" \
  --published-at "{日期}" --claim "{该页面支持的具体主张}" --status verified
```

优先原始报告、官方文档和当事方信息。聚合页只能帮助找线索，不能替代原始来源。用户
提供但无法联网核对的材料标为 `user_provided`；不得把模型记忆标为 `verified`。

搜索不可用时，只写不依赖最新数据的分析、经验和明确的个人判断；删除无法核实的数字、
引述和“研究显示”。记录降级并提醒发布前补证据。

## 4. 写作

读取存在的 `{home}/playbook.md`，只执行置信度不低于 5 的规则；2-5 作为参考，低于 2
忽略。读取最近三篇历史，避免机械复用同一开头、结构和收尾。

范文库存在时最多读取 2 篇最相关范文，只模仿节奏与语气，不复用观点和句子；记录实际
使用的范文路径。范文库为空时直接按账号风格写，不加载通用假范文。

写作要求：

- 标题准确、有明确对象和利益点，不夸大；正文通常 1200-2500 字，可按题目调整。
- 先讲清核心判断，再用事实、场景或步骤支撑；每一节都推动文章，不凑字数。
- 明确区分事实、推断和个人意见；不为“像人”刻意插入错句、负面情绪或离题段落。
- 账号声音来自 style、persona、范文和用户学习规则，不来自统一的口语模板。
- 禁止编造亲历、身份、采访、数字、评价和引用。

若 `flags.use_writer_model=true`，将框架、已核实素材、来源编号、风格和上述要求写入本任务
目录的 `brief.md`，再调用 `wewrite llm-write` 写到文章路径；失败则直接写作。否则由当前
Agent 直接写。两种方式都要在出稿后通读一次并修正事实归属、重复和跳跃。

完成后更新任务，至少包括文章路径、框架、人格、字数和来源/范文/学习规则记录：

```bash
wewrite run update --patch '{"framework":"...","persona":"...","word_count":0,"provenance":{"verified_sources":0,"unverified_sources":0,"exemplars":[],"playbook_rules":[]}}'
wewrite run step write completed
```

单独调用时告诉用户文章路径，并建议继续 `wewrite-review`。
