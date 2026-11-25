# 公众号文章配图 Skill

这是一个给公众号文章配图的 AI Agent 技能。给它一篇草稿，Agent 会拟一段导语，并为封面、开篇和正文插图写好生图提示词。你确认提示词后，脚本会批量生成图片并保存到本机。

## 使用前准备

- 本机需安装 Python 3.10 或更新版本，并能访问生图服务。用 Agent 时，它还需要能读取文章和 [SKILL.md](SKILL.md)，并运行本地脚本。
- 准备 APIMart 或兼容服务的 HTTPS 基础地址和 API Key。服务需要支持 `gpt-image-2`、`POST /v1/images/generations` 和 `GET /v1/tasks/{task_id}`。实际生图会消耗服务额度。

在项目根目录将 [.secrets.example.json](.secrets.example.json) 复制为 `.secrets.json`。已有配置时直接编辑原文件。填写 `profiles.primary` 下的 `api_base` 和 `api_key`，并确认 `active_profile` 指向这组配置。`backup` 可留空。在 macOS 或 Linux 上可用 `chmod 600 .secrets.json` 限制读写权限。打包或上传 Skill 时请排除私密文件。

## 怎么用

**用 AI Agent。** 提供文章文件或正文，让 Agent 按 [SKILL.md](SKILL.md) 执行。可以直接这样提需求。

> 给这篇公众号文章做一张封面和几张正文插图，包含一张开篇图。先给我看导语和完整提示词，等我确认后再生成图片。

**直接运行脚本。** 如果已有生图任务 JSON，在项目根目录运行下方命令。任务格式和开篇插图要求见 [SKILL.md 的 JSON 任务说明](SKILL.md#json-任务)。

```bash
python3 scripts/generate_wechat_images.py path/to/tasks.json
```

图片默认保存到 `~/AI-generated-images/` 下以时间和文章标题命名的子目录。打开其中的 `preview.html` 可以逐张检查。

## 工作原理

Agent 根据文章写提示词，将你确认的内容整理成任务 JSON。Python 脚本读取本机选中的 URL 和 Key，向生图服务提交任务。提交完成后默认等待 90 秒，之后每 45 秒查询一次未完成的任务。图片生成后下载到本机。任务记录保存在 `manifest.json`，可用于恢复执行。

## 详细用法

- 任务字段、提示词规则、参考图和中断恢复见 [SKILL.md](SKILL.md)。
- 查看所有命令行参数可运行 `python3 scripts/generate_wechat_images.py --help`。常用参数有 `--profile backup`（临时换一组配置）和 `--dry-run`（只验证任务并生成预览）。

许可证为 [MIT](LICENSE)。
