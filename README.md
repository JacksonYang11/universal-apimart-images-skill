# Universal WeChat APIMart Image Generator

通用微信公众号文章 APIMart 批量生图技能。根据文章内容自动生成推文导语、封面图和正文插图提示词，通过 APIMart `gpt-image-2` 模型批量生成、轮询、下载和通知。

## 快速开始

### 环境要求

- Python 3.8+
- APIMart API Key（从 [APIMart](https://api.apimart.ai) 获取）

### 设置 API Key

```bash
export APIMART_API_KEY="你的API密钥"
```

### 生成图片

1. 准备一个 JSON 任务文件（见下方格式）。
2. 在项目根目录运行脚本：

```bash
python3 "scripts/generate_wechat_images.py" "path/to/tasks.json"
```

## JSON 任务文件格式

```json
{
  "article_title": "文章标题",
  "article_source": "文章来源（文件路径/conversation/pasted_text）",
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

### 字段说明

| 字段 | 说明 |
|------|------|
| `article_title` | 文章标题，用于输出文件夹命名 |
| `article_source` | 文章来源记录 |
| `wechat_intro` | 推文导语 |
| `output_dir` | 输出目录，默认 `~/AI-generated-images` |
| `images[].name` | 英文/数字/下划线命名 |
| `images[].usage` | 中文用途或插入位置描述 |
| `images[].prompt` | 中文生图提示词 |
| `images[].refs` | 可选参考图（公网 URL 或本地路径） |
| `images[].task_id` | 可选，恢复执行时使用 |

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `json_file` | JSON 任务文件路径（必填） | - |
| `--api-key` | APIMart API Key | 环境变量 `APIMART_API_KEY` |
| `--api-base` | API 基础 URL | `https://api.apimart.ai` |
| `--output-dir` | 输出根目录 | JSON 中的 `output_dir` 或 `~/AI-generated-images` |
| `--run-dir` | 指定输出目录（用于恢复执行） | - |
| `--initial-wait` | 任务提交后等待秒数 | `60` |
| `--poll-interval` | 轮询间隔秒数 | `30` |
| `--timeout` | 总超时秒数 | `900` |
| `--dry-run` | 仅验证和预览，不调用 API | `false` |
| `--no-notify` | 禁用完成通知 | `false` |

## 执行流程

1. 读取 JSON 任务文件，验证所有字段。
2. 提交全部生图任务至 APIMart `gpt-image-2`（分辨率 `1k`，尺寸 `16:9`）。
3. 待所有任务获取到 `task_id` 后，等待 60 秒。
4. 每 30 秒批量轮询一次任务状态。
5. 全部任务完成后统一下载图片。
6. 下载全部成功后播放声音并弹窗通知。

## 恢复执行

如果已有 `task_id`，可在 JSON 中添加 `task_id` 字段避免重复提交：

```json
{
  "name": "cover",
  "usage": "文章总封面",
  "task_id": "task_xxx",
  "prompt": "...",
  "refs": []
}
```

使用 `--run-dir` 指向已有输出目录：

```bash
python3 "scripts/generate_wechat_images.py" "tasks-resume.json" --run-dir "~/AI-generated-images/20240101_120000_某文章"
```

## 失败处理

- **任务失败/超时**：不下载、不弹通知，报告具体失败任务。
- **下载失败**：保留已下载文件，报告下载失败项，不弹通知。
- 不会自动重跑失败任务（避免额度消耗）。

## 输出

图片输出至 `output_dir` 下的 `{时间戳}_{文章标题}` 子目录，同时生成 `manifest.json` 记录完整任务信息。

## 项目结构

```
universal-wechat-apimart-images/
├── scripts/
│   └── generate_wechat_images.py   # 核心生图脚本
├── SKILL.md                        # 技能描述文档（供 AI 智能体使用）
└── README.md                       # 本文件
```

## 许可证

MIT
