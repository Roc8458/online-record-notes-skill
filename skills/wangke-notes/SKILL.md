---
name: wangke-notes
description: Use when 用户要记录网课整理成笔记。录音转写后生成七模块笔记存 Obsidian。
version: 1.0.0
author: Roc Wan
license: MIT
metadata:
  hermes:
    tags: [网课, 笔记, 录音, 转写, whisper, obsidian]
---

# 网课笔记 · Wangke Notes

记录电脑正在播放的网课（系统声音）→ 本地转写 → 七模块结构化笔记 → 存进 Obsidian 并更新总览画板。全程本地处理，音频不出电脑。

## 触发词

- 「开始记录网课」「记录网课」「开始录音」→ 启动后台录音
- 「停止记录，整理成笔记」「停止并整理」「结束网课记录」→ 停止录音 + 转写 + 整理 + 存笔记

## 配置区（安装后必读，见 README.md）

| 配置项 | 位置 | 默认值 |
| --- | --- | --- |
| Obsidian vault 路径 | 下方「目录约定」 | `C:\Users\<用户名>\OneDrive\Notes`（首次使用先向用户确认实际路径） |
| 转写模型路径 | `scripts/transcribe.py` 顶部 `MODEL_PATH` | `D:/hf-whisper/faster-whisper-large-v3` |
| Python 依赖 | `scripts/requirements.txt` | 安装命令见 README |

## 目录约定

- Obsidian vault：`C:\Users\<用户名>\OneDrive\Notes`（先向用户确认实际 vault 路径）
- 笔记根：`<vault>\网课笔记\`
- 总览画板：`<vault>\网课笔记\📊 网课总览.md`
- **每节课一个项目文件夹**：`网课笔记\YYYY-MM-DD 课程名\`，内含：
  - `录音\` — 录音分段目录（seg_0001.wav 每 60 秒一段 + manifest.json + 合并的 _merged.wav）
  - `原始记录.md` — 转写逐字稿（带时间戳）
  - `笔记.md` — 七模块结构化笔记（思维导图放在最开头）
  - `思维导图.excalidraw.md` — 手绘风思维导图（Obsidian Excalidraw 新格式）

## 录音流程

1. 用户说「开始记录网课」时：
   - 先问课程名（用于文件夹命名），如「深度学习第3讲」
   - 后台启动录音脚本，**后台运行不打断用户看课**
   - 告知用户「开始录音了，看完课说『停止并整理』」
2. 录音脚本：`scripts/record.py`（sounddevice WASAPI loopback 录系统声音，输出 wav）
   - 后台启动：`python <skill_dir>/scripts/record.py <输出目录>`，用 terminal background=true 启动，**不阻塞对话**
   - 脚本自动探测 loopback 设备（设备名关键字匹配，实测有效设备：Realtek HD Audio output with SST）

## 转写流程

1. 用户说「停止记录」时：**在录音输出目录创建 `stop.flag` 文件**（用 write_file 写一个空文件即可），脚本检测到后优雅保存退出
   - 录音脚本每 60 秒落盘一段 `seg_XXXX.wav`，即使异常被杀，已落盘的分段完好（转写脚本直接读目录合并）
   - 注意：部分 Agent 环境后台进程 stdin 不可用，不要用 process write/submit 停录音；用 stop.flag 文件
2. 运行转写：`python <skill_dir>/scripts/transcribe.py <录音目录> <原始记录.md>`（目录含 seg_*.wav，自动合并）
   - faster-whisper **large-v3（int8）** 模型，中文，输出带时间戳文本
   - 1 小时音频约 25-40 分钟，用后台任务跑，完成通知后再继续
3. 转写完成后读入 `原始记录.md` 全文

## 七模块笔记规则（笔记.md）

从转写稿提炼，严格按以下结构：

```
# <课程名>

**日期**：<日期>　**时长**：<录音时长>　**模型**：whisper-large-v3

## 🗺️ 思维导图
![[思维导图.excalidraw.md]]

## 📌 一句话总结
<50 字以内说清这节课讲什么>

## 🧠 核心内容
<知识点提炼，每个点一段：标题 + 2-4 句解释，按课程逻辑排序>

## 📚 智能章节
<按知识结构分章节，每章：标题 + 开始时间戳 + 1-2 句内容概括>

## 🎯 重点结论
<这节课最核心的观点/考点/结论，3-8 条，每条一句话>

## 💎 金句时刻
<老师说的好句，原句引用 + 时间戳，1-5 条>

## 📜 原始记录
<完整转写稿原文，按章节分段>
```

思维导图生成规则：
- 每次生成笔记时，同时生成一张手绘风思维导图 `思维导图.excalidraw.md`（同课程文件夹下），放在笔记正文**最开头**（标题和日期行之后）
- **必须用 Obsidian Excalidraw 插件的新格式**（纯 .excalidraw JSON 会被提示"旧版格式"）：
  - 文件头：`---\nexcalidraw-plugin: parsed\ntags:\n  - excalidraw\n---\n\n# 思维导图\n\n==⚠ Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠==\n\n# Drawing\n\n```json\n<完整 excalidraw JSON>\n```\n`
  - 元素格式：形状 + boundElements/containerId 绑定文字 + 箭头
- 结构：中心椭圆=课程主题；2-4 个分支=大知识点（矩形+淡色）；子节点=具体要点；箭头连接
- 节点文字短句（≤15 字），分支用不同淡色系（蓝/绿/紫/橙）

其他规则：
- 金句必须是原话引用，不润色；没有金句就写「（本节无金句）」不硬凑
- 章节时间戳来自转写稿，格式 `[MM:SS]`
- 术语保持原样，转写错的专业术语根据上下文修正
- 笔记.md 的 frontmatter：

```yaml
---
course: <课程名>
date: <YYYY-MM-DD>
duration: <分钟数>
tags: [网课笔记]
summary: <一句话总结>
---
```

## Obsidian 落盘

1. 创建课程文件夹，写入 `原始记录.md`、`笔记.md`、`思维导图.excalidraw.md`（`录音\` 分段目录已由录音脚本写入）
2. **更新总览画板** `📊 网课总览.md`：
   - 首次使用：创建画板文件，写入 Dataview 查询块 + 说明
   - 画板靠 Dataview 自动汇总（按 date 排序），笔记 frontmatter 完整即可
   - 画板内容：
     ```
     # 📊 网课总览
     ```dataview
     TABLE date as 日期, summary as 一句话总结, duration as 时长(分钟)
     FROM "网课笔记"
     WHERE contains(tags, "网课笔记")
     SORT date DESC
     ```
     ```
3. 完成后告知用户：笔记路径 + 一句总结 + 「已更新总览画板」

## 常见坑

1. **录音录不到声音**：sounddevice WASAPI loopback 设备名随驱动变（Realtek/THX/Nahimic 多套设备）。脚本会自动探测 loopback 设备，失败时列出可用设备让用户指认。
2. **用户中途换课**：新课程要重新说「开始记录网课」，一节课一个文件夹。
3. **转写很慢别催**：后台任务跑，完成通知后再继续，别中途 poll。
4. **m4a 不直接转**：录音脚本输出 wav，转写脚本也支持 m4a/mp3（faster-whisper 内部解码），用户如果自己录了 m4a 也能用。
5. **总览画板不显示**：检查笔记 frontmatter 的 tags 含「网课笔记」，且文件在「网课笔记」文件夹下（Dataview FROM 路径匹配）。
6. **传路径必须用 Windows 原生格式**：`C:\Users\...` 或 `C:/Users/...`，不要用 bash 的 `/c/Users/...`（MSYS 风格，PyAV 不认，会 FileNotFoundError）。
7. **报 `cublas64_12.dll not found`**：ctranslate2 4.8+ 不含 CUDA 库。两步解决：① `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`；② 脚本里必须 `os.add_dll_directory(site-packages/nvidia/*/bin)` + `ctypes.WinDLL("cublas64_12.dll")` 预加载（仅 add_dll_directory 无效，ctranslate2 运行时 LoadLibrary 不认；预加载后同名 DLL 直接复用）。transcribe.py 已内置此逻辑。

## 验证清单

- [ ] 录音脚本在用户机器能录到系统声音（wav 文件非静音）
- [ ] 转写脚本输出中文带时间戳文本
- [ ] 笔记.md 七模块齐全、思维导图在开头、frontmatter 完整
- [ ] 总览画板 Dataview 能列出新笔记
