---
name: universal-wechat-apimart-images
description: 通用微信公众号文章 APIMart 批量生图技能。用于 Trae/DeepSeek、Claude Code、ChatGPT 或其他能读取本地 Markdown 并运行脚本的智能体。根据指定文章生成推文导语、封面图和正文插图提示词，用户确认后调用本地脚本通过 APIMart gpt-image-2 批量生成、轮询、下载和通知。
---

# 通用微信公众号 APIMart 批量生图技能

## 用途

为微信公众号文章生成推文导语、1 张封面图和 4-5 张正文插图，并通过 APIMart `gpt-image-2` 批量生图。

本技能是通用版，不依赖 Codex 的 `.codex/skills` 机制。其他智能体只需要读取本文件，并在本技能目录内运行脚本：

```text
scripts/generate_wechat_images.py
```

## 执行原则

不要在用户确认提示词前调用 APIMart。

流程必须是：

1. 确认文章来源。
2. 读取文章正文。
3. 生成推文导语、封面图提示词、正文插图提示词。
4. 先展示给用户确认或修改。
5. 用户确认后生成 JSON 任务文件。
6. 调用 `scripts/generate_wechat_images.py`。
7. 脚本完成后报告输出目录和失败情况。

## 文章来源

接受以下文章来源：

- 用户直接粘贴文章正文。
- 用户提供本地文件路径，例如 `.md`、`.txt` 或其他可读取草稿。
- 用户说“这篇文章”，且当前上下文里只有一篇明显完整的文章。

如果存在多篇文章、多个版本或多个候选文件，先问用户确认，不要猜。

JSON 中记录 `article_source`：

- 文件来源：填写绝对路径。
- 当前对话：填写 `conversation`。
- 临时粘贴：填写 `pasted_text`。

## 提示词生成

使用用户常用要求：

```text
给文章设计封面图和插图，以及推文导语，导语要简洁精炼。封面内容精彩一点逼格高一点，插图四五张就行，要求文章内均匀分布，亮度要能看清画面，给出这些图片的生图提示词，用中文。直接回答就行，不要加进文章里
```

默认生成：

- 1 张封面图。
- 4-5 张正文插图。

提示词要求：

- 使用中文。
- 包含主体、场景、氛围、视觉风格、光线、构图和关键细节。
- 封面图要更有冲击力、更精致、更适合公众号封面。
- 插图要围绕文章结构均匀分布，并标明预期插入位置。
- 画面要明亮清晰，适合微信阅读。
- 不要在提示词里写 `16:9`、`1k` 等比例和分辨率，脚本会通过 API 参数控制。
- 除非用户明确要求，不要让模型生成中文文字、标志、水印、复杂图表或精确 UI。

给用户确认时使用这种结构：

```text
推文导语：
...

图片提示词：
1. 封面图｜文章总封面
提示词：...

2. 插图 01｜预计插入位置
提示词：...
```

## JSON 任务

用户确认后，生成 UTF-8 JSON 文件。结构如下：

```json
{
  "article_title": "文章标题",
  "article_source": "/Users/jackson/Documents/projects/Articles/path/to/article.md",
  "wechat_intro": "简洁推文导语",
  "output_dir": "~/AI-generated-images",
  "images": [
    {
      "name": "cover",
      "usage": "文章总封面",
      "prompt": "中文生图提示词",
      "refs": []
    },
    {
      "name": "illustration_01",
      "usage": "正文第一处插图",
      "prompt": "中文生图提示词",
      "refs": []
    }
  ]
}
```

字段规则：

- `article_title`：文章标题，用于输出文件夹命名。
- `article_source`：文章来源记录。
- `wechat_intro`：推文导语。
- `output_dir`：默认 `~/AI-generated-images`。
- `images[].name`：英文、数字、下划线命名，例如 `cover`、`illustration_01`。
- `images[].usage`：中文用途或插入位置。
- `images[].prompt`：最终中文生图提示词。
- `images[].refs`：可选参考图，支持公网 URL 或本地图片路径。

## 脚本命令

macOS / zsh：

```bash
# 确保当前 shell 已设置 APIMART_API_KEY
python3 "scripts/generate_wechat_images.py" "path/to/tasks.json"
```

不要让用户在聊天里粘贴 API key。脚本读取用户环境变量 `APIMART_API_KEY`。

脚本固定提交：

```json
{
  "model": "gpt-image-2",
  "resolution": "1k",
  "size": "16:9",
  "n": 1
}
```

脚本策略：

1. 先提交全部生图任务。
2. 全部拿到 `task_id` 后等待 180 秒。
3. 每 60 秒批量轮询所有任务。
4. 所有任务都生成成功并拿到图片 URL 后，统一下载全部图片。
5. 全部下载成功后，才播放声音和弹窗通知。

## 恢复执行

**恢复前，必须先读 `--run-dir` 目录下的 `manifest.json`，从中提取每个任务的 `task_id`，写入要传给脚本的 JSON 文件中。** 否则脚本会因为没有 `task_id` 而重新提交生图任务，消耗额外额度。

把 `task_id` 写入对应图片对象：

```json
{
  "name": "cover",
  "usage": "文章总封面",
  "task_id": "task_xxx",
  "prompt": "中文生图提示词",
  "refs": []
}
```

如需继续写入原目录：

```bash
python3 "scripts/generate_wechat_images.py" "path/to/tasks-resume.json" --run-dir "~/AI-generated-images/existing-run-folder"
```

## 失败处理

- 任意生图任务失败或超时：不要开始下载，不弹成功通知，报告失败任务。
- 全部生图成功但某张下载失败：保留已下载文件，报告下载失败，不弹成功通知。
- 不要在用户未要求时自动重跑失败任务，因为可能消耗额度。

## AI 智能体行为铁律（防止误判卡死、浪费额度）

生成脚本的输出时间线是：**提交所有任务（秒级）→ 静默等 180 秒 → 每 60 秒轮询一次**。从启动到第一次有意义的轮询输出，至少需要 3 分钟以上。因此 AI 智能体在监控脚本运行时必须遵守以下规则：

1. **启动后第一次检查至少要等 3 分钟以上。** 建议节奏：180s → 60s → 60s → 60s 逐步检查，而不是 30s 起步频繁查询。
2. **绝不可以凭"输出为空"就判卡死。** 异步脚本在初始等待期内和轮询间隔内输出为空是完全正常的。
3. **不确定是否真卡死时，先查输出目录的 `manifest.json`。** 如果 `manifest.json` 已存在且其中每张图片都有 `task_id` 和 `status: "submitted"`，说明任务已提交成功，脚本只是在等轮询，绝不能停掉重跑。重跑会导致重复提交新任务，白白消耗图片额度。
4. **只有在以下情况才能判定脚本异常并终止：**（a）脚本进程已退出且退出码非 0；（b）超过 20 分钟仍无任何输出也无 manifest.json 生成；（c）manifest.json 明确记录了 `submit failed` 错误。
