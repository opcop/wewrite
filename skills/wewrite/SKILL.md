---
name: wewrite
description: |
  微信公众号内容全流程主入口：选题、素材、写作、审稿、配图、排版与草稿箱发布。
  也负责把风格设置、学习修改、数据复盘和多平台改写分发给对应 wewrite-* 模块。
  触发关键词：公众号、微信文章、微信推文、草稿箱、微信排版、写公众号、写一篇。
  通用文章、博客、邮件、短视频和网站 SEO 不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - WebSearch
  - WebFetch
---

# WeWrite — 公众号内容主入口

## 运行原则

- 默认连续完成，不在每一步停下来。用户说“交互模式”时，才在选题、框架和配图处确认。
- 每篇文章必须用独立任务目录，不能覆盖另一篇文章。
- “写一篇”默认只交付审过的本地稿；生成图片和发布都不是默认动作。
- 只有用户明确说“完整制作”才生图和排版；只有明确说“推到草稿箱/发布”才允许调用发布命令。
- 搜索失败时可以继续写分析和经验判断，但不得把模型记忆包装成已核实的事实。

`{home}` 是 `wewrite home` 返回的状态目录。`{skill_dir}` 是本 skill 目录。确定性操作走 `wewrite` 命令。

## 路由

| 用户意图 | 模块 |
|---|---|
| 重设风格 | `wewrite-style` |
| 只要选题 | `wewrite-topic` |
| 检查文章 | `wewrite-review` |
| 封面或配图 | `wewrite-visual` |
| 排版、预览、草稿箱、图片帖 | `wewrite-publish` |
| 学习修改、范文、主题 | `wewrite-learn` |
| 数据复盘 | `wewrite-stats` |
| 多平台改写 | `wewrite-rewrite` |

环境有 Skill 工具时激活同名 skill；否则完整读取兄弟目录的 `SKILL.md` 后执行。

## 完整流程

### 1. 建立或恢复任务

先运行 `wewrite diagnose --json`。命令缺失或依赖失败才引导安装；缺少风格文件是正常首次设置，转 `wewrite-style`。

根据用户原话选择模式：

```bash
# 默认“写一篇”：不生图、不发布
wewrite run start --topic "{选题，可空}" --mode draft --visual-mode none

# “完整制作”：生成图片并做本地预览，不发布
wewrite run start --topic "{选题，可空}" --mode complete --visual-mode full --max-images 4

# “推到草稿箱”：用户已明确授权发布
wewrite run start --topic "{选题，可空}" --mode publish --visual-mode full --max-images 4
```

把 diagnose 的 flags 和当天日期写入任务：

```bash
wewrite run update --patch '{"flags": {"skip_publish": false, "skip_image_gen": false, "use_writer_model": false, "needs_onboard": false, "diagnosed_at": "YYYY-MM-DD"}}'
```

如果用户说“继续上次”，先 `wewrite run list`，明确唯一任务后 `wewrite run resume <run_id>`；不要新建任务。

### 2. 选题

用户已给选题就记录并跳过选择；否则执行 `wewrite-topic`。完成后：

```bash
wewrite run step topic completed
```

### 3-4. 框架、素材与写作

执行 `wewrite-write`。文章必须保存到 `wewrite run show` 返回的 `artifacts.article`，所有网页素材同步记录到本任务的 `sources.yaml`。

### 5. 编辑审稿

执行 `wewrite-review`。事实、观点、实用性、账号声音和可读性是主标准；工具分数只提示可能的问题。

### 6. 视觉

- `visual.mode=none`：跳过。
- `visual.mode=prompts` 或缺少图片配置：只保存提示词。
- `cover/full`：执行 `wewrite-visual`，严格遵守 `max_images` 与 `max_cost`。

### 7. 排版与发布

执行 `wewrite-publish`。只有 `permissions.publish=true` 且发布配置可用、封面存在时才推草稿箱；其他情况一律生成本地预览。

### 8. 收尾

确认文章和预览等产物存在，再执行：

```bash
wewrite run finish
```

该命令负责封存任务并写历史，不要手工追加 `history.yaml`。最后告诉用户标题、文章路径、来源数量、图片/预览结果、是否进入草稿箱，以及发生的降级。

## 失败与恢复

步骤失败时记录：

```bash
wewrite run step <topic|write|review|visual|publish> failed --error "简短原因"
```

保留当前任务和已有产物。下次恢复后只重做失败或未完成的步骤。发布失败要回退到本地预览；图片失败要保留提示词；搜索失败要删掉无法核实的具体数字和引述。
