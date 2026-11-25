# 公众号文章配图 Skill

这是一个给公众号文章配图的 AI Agent 技能。给它一篇草稿，Agent 会拟一段导语，并为封面、开篇和正文插图写好生图提示词。你确认提示词后，脚本会批量生成图片并保存到本机。

## 使用前准备

- 本机需安装 Python 3.10 或更新版本，并能访问生图服务。用 Agent 时，它还需要能读取文章和 [SKILL.md](SKILL.md)，并运行本地脚本。
- 准备 APIMart 或兼容服务的 HTTPS 基础地址和 API Key。服务需要支持 `gpt-image-2`、`POST /v1/images/generations` 和 `GET /v1/tasks/{task_id}`。实际生图会消耗服务额度。

在项目根目录将 [.secrets.example.json](.secrets.example.json) 复制为 `.secrets.json`。已有配置时直接编辑原文件。填写 `profiles.primary` 下的 `api_base` 和 `api_key`，并确认 `active_profile` 指向这组配置。`backup` 可留空。在 macOS 或 Linux 上可用 `chmod 600 .secrets.json` 限制读写权限。打包或上传 Skill 时请排除私密文件。

## 怎么用

**用 AI Agent。** 提供文章的 Markdown 文件，让 Agent 按 [SKILL.md](SKILL.md) 执行。可以直接这样提需求。

> 给这篇公众号文章做一张封面和几张正文插图，包含一张开篇图。先给我看导语和完整提示词，等我确认后再生成图片。

未指定画风时，Agent 默认采用新工笔国风。脚本默认请求适合公众号配图的 `16:9` 横图。

**直接运行脚本。** 如果已有生图任务 JSON，在项目根目录运行下方命令。任务格式和开篇插图要求见 [SKILL.md 的 JSON 任务说明](SKILL.md#json-任务文件格式)。

```bash
python3 scripts/generate_wechat_images.py path/to/tasks.json
```

图片保存到文章所在目录下的 `AI-generated-images/`。新分组遇到已有目录时，依次使用 `AI-generated-images1/`、`AI-generated-images2/` 等。下载完成后，由用户打开其中的 `preview.html` 逐张检查。

## 配图分组与输出目录

一组 = 一套图（封面 + 开篇 + 各章节插图），同一组的图片落在同一个文件夹。

- 任务 JSON 的 `article_source` 要填文章 Markdown 的真实路径，脚本据此定位文章目录并下载图片。
- `group` 标识一组配图：同一 `group` 再次执行会复用原目录，并跳过已下载的图片；换新一组则新建编号目录。
- 未填 `group` 时，每次运行都视为新组。
- `article_source` 无法定位文章目录时，脚本会告警，默认回退到 `~/Pictures/AI-generated-images/{时间戳}_{标题}`。正常配图流程须提供文章的真实路径。
- 记下脚本打印的 `Output folder`，该组后续的生成、恢复和展示都只用这个目录。

## 工作原理

Agent 根据文章拟导语和提示词，并将你确认的内容整理成任务 JSON。Python 脚本读取本机选中的 URL 和 Key，向生图服务提交任务。提交完成后默认等待 120 秒，之后每 60 秒查询一次未完成的任务。图片生成后下载到本机。任务记录保存在 `manifest.json`，可用于恢复执行。

## 详细用法

- 任务字段、提示词规则、参考图和中断恢复见 [SKILL.md](SKILL.md)。
- 查看所有命令行参数可运行 `python3 scripts/generate_wechat_images.py --help`。常用参数有 `--profile backup`（临时换一组配置）、`--run-dir`（明确指定恢复时使用的分组目录）、`--output-dir`（文章目录无法定位时的兜底根目录）和 `--dry-run`（只验证任务并生成预览）。

许可证为 [MIT](LICENSE)。
