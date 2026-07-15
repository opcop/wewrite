---
name: wewrite-visual
description: |
  WeWrite 视觉模块：为公众号文章生成封面和必要的内文配图，或只交付提示词。触发词：
  封面图、公众号配图、给文章配图、换封面。通用绘图和 logo 设计不触发。
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# wewrite-visual — 封面与配图

## 前置

用户指定文章时使用该文件；否则 `wewrite run show`，读取 `artifacts.article`、`visual`、
`flags` 和任务目录。进入时 `wewrite run step visual in_progress`。

`visual.mode=none` 时标记 skipped 并结束。`prompts` 或 `skip_image_gen=true` 时仍要完成提示词，
但不调用付费图片服务。

完整读取：

```text
读取: {skill_dir}/references/visual-guide.md
```

## 执行

1. 从终稿提取 3-5 个具体实体和文章主情绪，形成统一色板、构图与质感。
2. 写一个封面提示词。`cover` 模式到此为止；`full` 模式只为确实需要解释或缓冲阅读的
   段落补图，不按固定数量凑图。
3. 将提示词和目标路径写到任务目录的 `image-prompts.md`；批量清单写到 `images.json`。
4. 数量必须不超过任务的 `visual.max_images`。调用时同时传入数量和费用上限：

```bash
wewrite image-gen --manifest {run_dir}/images.json --max-images {max_images} --max-cost {max_cost}
```

`max_cost` 为空时省略该参数。预算预检不通过就减少内文图，不能绕过上限。图片服务失败时
保留完整提示词并继续流程。

5. 一次性检查所有实际文件：能打开、格式与扩展名一致、核心实体可辨、风格连贯。只重试
明显失败的单张一次。将采用的内文图插到相应段落，封面不插入正文。

完成后更新 `images.cover`、`images.figures`、`artifacts.image_prompts`，再执行：

```bash
wewrite run step visual completed
```

只有提示词时同样标 completed，并明确说明未产生费用、没有实际图片。
