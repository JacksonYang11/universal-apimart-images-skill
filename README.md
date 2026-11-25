# 公众号文章配图 Skill

给一篇公众号文章，自动想好封面和插图，批量生成图片存到本机。

## 这是什么

一个给公众号文章配图的工具。你把写好的文章 Markdown 交给它，它会：

- 拟一段推文导语；
- 给封面、开头和正文各章节分别写好生图提示词；
- 你确认提示词后，调用 APIMart 的生图服务批量出图，并下载到本机。

## 用来干什么

一篇推文通常需要一张封面、一张开头图、每节一张插图。这个工具一次把这套图做完，图片放在文章自己的文件夹里，再配一个预览页，方便你逐张检查。

默认出 16:9 横图，默认新工笔国风。你有别的画风要求时，以你的要求为准。

## 准备工作

1. Python 3.10 或更新版本。
2. 一个 APIMart 或兼容服务的地址和 API Key，接口要支持 `gpt-image-2` 和任务查询。生成图片会消耗服务额度。
3. 在本目录把 [.secrets.example.json](.secrets.example.json) 复制成 `.secrets.json`，填好 `api_base` 和 `api_key`。macOS 或 Linux 上可以 `chmod 600 .secrets.json` 收紧权限。

## 怎么用

**推荐让 AI Agent 来做。** 把文章 Markdown 的路径交给它，直接说：

> 给这篇文章配图，一张封面、一张开头图、每节一张插图。先给我看导语和提示词，我确认后再生成。

Agent 会先列出导语和每张图的提示词，等你确认或改完，才真正开始生图。生成完会告诉你图片存在哪个文件夹，打开里面的 `preview.html` 一张张看就行。

**也可以自己跑脚本。** 已经有任务 JSON 时，在本目录运行：

```bash
python3 scripts/generate_wechat_images.py path/to/tasks.json
```

## 图片存在哪

存在文章所在的文件夹里，新建一个 `AI-generated-images` 目录。同一篇文章再生成一套，会依次用 `AI-generated-images1`、`AI-generated-images2`……

脚本运行结束会打印 `Output folder`，那就是这一套图的位置。之后查看、补图、续跑，都以这个目录为准。

## 大概怎么工作

1. Agent 读文章，拟导语，给每张图写提示词，交给你确认。
2. 确认后的内容整理成任务 JSON，脚本据此向生图服务提交任务。
3. 先等 2 分钟，之后每分钟查一次进度，出图就下载。
4. 进度记在同目录的 `manifest.json` 里。中途断了，用同一组继续跑就行，已经下好的图不会重复生成。

## 更多细节

提示词的写法和质量要求、任务 JSON 的字段、命令行参数、断点续跑和失败处理，都在 [SKILL.md](SKILL.md) 里。想直接看全部参数，运行：

```bash
python3 scripts/generate_wechat_images.py --help
```

许可证为 [MIT](LICENSE)。
