---
name: online-record-notes
description: Use when 用户要记录网课整理成笔记。录音转写后生成七模块笔记存 Obsidian。
version: 1.0.0
author: Roc Wan
license: MIT
metadata:
  hermes:
    tags: [网课, 笔记, 录音, 转写, whisper, obsidian]
    related_skills: [video-transcript-extraction]
---

# 网课笔记 · Online Record Notes

记录电脑正在播放的网课（系统声音）→ 本地转写 → 七模块结构化笔记 → 存进 Obsidian 并更新总览画板。全程本地处理，音频不出电脑。

## 触发词

- 「开始记录网课」「记录网课」「开始录音」→ 启动后台录音
- 「停止记录，整理成笔记」「停止并整理」「结束网课记录」→ 停止录音 + 转写 + 整理 + 存笔记

## 目录约定

- Obsidian vault：`C:\Users\84583\OneDrive\Notes`
- 笔记根：`C:\Users\84583\OneDrive\Notes\Online笔记\`（⚠️ 不是「网课笔记」，用户实际用的是 Online笔记）
- 总览画板：`C:\Users\84583\OneDrive\Notes\Online笔记\📊 网课总览.md`
- **录音文件放 D 盘**（用户要求不占 C 盘）：`D:\ai recording\YYYY-MM-DD 课程名\录音\`（seg_0001.wav 每 60 秒一段 + manifest.json）
- **笔记文件放 Online笔记**：`Online笔记\YYYY-MM-DD 课程名\`，内含：
  - `原始记录.md` — 转写逐字稿（带时间戳）
  - `笔记.md` — 七模块结构化笔记（含思维导图嵌入）
  - `思维导图.excalidraw.md` — 手绘风思维导图（Obsidian Excalidraw 新格式）

## 录音流程

1. 用户说「开始记录网课」时：
   - **不问课程名，直接开录**：用录制日期临时命名（如 `2025-09-04 网课`）
   - 创建录音目录：`D:\ai recording\YYYY-MM-DD 网课\录音\`（📌 录音不占 C 盘）
   - 启动录音 + 哨兵，告知用户「开始录了，去看课吧」
   - 结束后根据转写内容重命名文件夹（简短，如「remotion入门」「深度学习3」）
2. 录音脚本：`scripts/record.py`（pyaudiowpatch WASAPI loopback 录系统声音，输出 wav）
   - 依赖：`pip install pyaudiowpatch`（已装 hermes venv；sounddevice 的 WDM-KS/WASAPI 在本机已失效 PaErrorCode -9996）
   - **必须用独立进程启动**：`python <skill_dir>/scripts/start_record_detached.py "D:/ai recording/<日期 课程名>/录音"`（DETACHED 无窗口，脱离 Hermes 进程管理——2026-08-27 实测 Hermes 管理的后台进程会被偶发误杀，独立进程不会）
   - 日志写到 `<录音目录>/record.log`（心跳每 10s：callbacks/content_sec/segs），排障看这里
   - 脚本自动找 WASAPI 默认输出设备的 loopback（设备名形如「扬声器 (Realtek(R) Audio) [Loopback]」）
   - ⚠️ WASAPI loopback 只在系统有声音输出时产生数据：静音时段无回调、内容自然跳过；开始录音后要确认课程声音在播放
   - 分段按「内容时长 60s」落盘（静音不拖延）；**启动时自动继承已有 seg 编号**（重启不覆盖旧文件，文件名顺序=时间顺序）
   - **录音哨兵**：cron 任务「网课录音哨兵」（job_id=`a84f9f008220`, every 2m, no_agent, `hermes/scripts/record_sentinel.py`）自动保活——进程死了/卡死自动重启并通知
     - ⚡ **每次录音自动启用**：启动录音后立即 `cronjob action=resume job_id=a84f9f008220` 恢复哨兵；停止录音后 `cronjob action=pause job_id=a84f9f008220` 暂停哨兵（平时不跑，省资源）
     - 换新课时哨兵自动发现最新目录（D:\ai recording 下最新）

## 转写流程

1. 用户说「停止记录」时：**在录音输出目录创建 `stop.flag` 文件**（用 write_file 写一个空文件即可），脚本检测到后优雅保存退出
   - 同时 `cronjob action=pause job_id=a84f9f008220` 暂停录音哨兵
   - 录音脚本每 60 秒落盘一段 `seg_XXXX.wav`，即使异常被杀，已落盘的分段完好（转写脚本直接读目录合并）
   - 注意：Hermes 后台进程 stdin 不可用，不要用 process write/submit 停录音；用 stop.flag 文件
2. 运行转写：`python <skill_dir>/scripts/transcribe.py <录音目录> <原始记录.md>`（目录含 seg_*.wav，自动合并）
   - faster-whisper **large-v3（int8）** 模型，路径 `D:/hf-whisper/faster-whisper-large-v3`，中文，输出带时间戳文本
   - 1 小时音频约 25-40 分钟，用后台任务跑，完成通知后再继续
3. 转写完成后读入 `原始记录.md` 全文

## 七模块笔记规则（笔记.md）

> 笔记生成后必须做「内容标签 + 八大类入口 + wiki 联动」三步（见下方「归档联动」），
> 用户要求网课笔记统一存 `Online笔记/` 下，并按内容引用到八大类文件夹。

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
- 节点文字短句（≤15 字），分支用不同淡色系（蓝/绿/紫/橙），参考 excalidraw 技能配色

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

1. 创建课程文件夹（`Online笔记\` 下），写入 `原始记录.md`、`笔记.md`、`思维导图.excalidraw.md`（`录音\` 分段目录已由录音脚本写入）
2. **更新总览画板** `Online笔记\📊 网课总览.md`：
   - 首次使用：创建画板文件，写入 Dataview 查询块 + 说明
   - 画板靠 Dataview 自动汇总（按 date 排序，日期越新越靠前），笔记 frontmatter 完整即可
   - 画板内容：
     ```
     # 📊 网课总览
     ```dataview
     TABLE date as 日期, summary as 一句话总结, duration as 时长(分钟)
     FROM "Online笔记"
     WHERE contains(tags, "网课笔记")
     SORT date DESC
     ```
     ```
3. **打内容标签**：`笔记.md` frontmatter 的 tags 不能只有 `[网课笔记]`，要按内容加 2~5 个主题标签（领域 + 主题词，如 `AI`、`就业`、`FDE`、`数据标注`、`算力部署`），参考 obsidian-auto-filer 标签规范
4. **八大类入口（引用）**：按内容主题把笔记引用到 obsidian-auto-filer 八大类对应位置——
   - 在目标文件夹创建入口笔记（文件名带日期，如 `2026-08-21 AI时代三大爆火岗位（网课）.md`）
   - 内容用 **Obsidian embed 引用**（`![[Online笔记/课程文件夹/笔记]]`），保持单一副本，不改动原笔记
   - 入口笔记 frontmatter 带 tags + `source: Online笔记/课程文件夹/笔记.md`
   - 分类参照 obsidian-auto-filer 八大类体系（身体/心理/思维/技能/财务/人际/社会/意义），一节网课常横跨 2~4 个类（例：就业→社会/职场规则/AI与就业、行业→社会/商业认知/AI行业分析、岗位能力→技能/专业能力/对应文件夹）
5. **Wiki 联动**：加载 `obsidian-llm-wiki` 技能，按 ingest 流程更新 wiki——
   - 先读 index.md 查重：内容与已有页重叠 → 更新旧页（bump updated、追加 sources），**不新建重复页**
   - 没有覆盖的实体/概念 → 新建概念页（frontmatter 完整、至少 2 出链）
   - 更新 index.md + log.md
6. 完成后跑 `python <obsidian-llm-wiki>/scripts/check_wikilinks.py <vault>` 验证（0 真实断链；附件引用和带 `.md` 后缀的合法引用会被脚本正确识别）
3. 完成后告知用户：笔记路径 + 一句总结 + 「已更新总览画板」

## 常见坑

1. **录音录不到声音**：① 先确认电脑在播放声音——WASAPI loopback 静音时不产生数据（callback 不触发，content_sec 不涨）；② 确认 pyaudiowpatch 已安装（sounddevice 的 WDM-KS 打开报 PaErrorCode -9996，已弃用，别再试回 sounddevice）；③ 看脚本 DEVICE 行确认找到「[Loopback]」设备。
2. **record.py 崩溃 AxisError: axis 1 out of bounds**：pyaudiowpatch callback 的 in_data 是一维字节流，必须 `np.frombuffer(...).reshape(-1, channels)` 再 mean(axis=1)，当前脚本已内置。
3. **录音进程被误杀/中断**：不要用 terminal background=true 跑录音（Hermes 会偶发清理后台进程，2026-08-27 实测中断一次）；必须用 start_record_detached.py 独立进程。若已用独立进程仍中断，查 record.log 尾部 + 哨兵 cron（record_sentinel.py）会自动重启。
2. **用户中途换课**：新课程要重新说「开始记录网课」，一节课一个文件夹。
3. **转写很慢别催**：后台任务跑，完成通知后再继续，别中途 poll。
4. **m4a 不直接转**：录音脚本输出 wav，转写脚本也支持 m4a/mp3（faster-whisper 内部解码），用户如果自己录了 m4a 也能用。
5. **总览画板不显示**：检查笔记 frontmatter 的 tags 含「网课笔记」，且文件在「Online笔记」文件夹下（Dataview FROM 路径匹配）。
6. **传路径必须用 Windows 原生格式**：`C:\Users\...` 或 `C:/Users/...`，不要用 bash 的 `/c/Users/...`（MSYS 风格，PyAV 不认，会 FileNotFoundError）。
7. **报 `cublas64_12.dll not found`**：ctranslate2 4.8+ 不含 CUDA 库。两步解决：① `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`；② 脚本里必须 `os.add_dll_directory(site-packages/nvidia/*/bin)` + `ctypes.WinDLL("cublas64_12.dll")` 预加载（仅 add_dll_directory 无效，ctranslate2 运行时 LoadLibrary 不认；预加载后同名 DLL 直接复用）。transcribe.py 已内置此逻辑。

## 验证清单

- [ ] 录音脚本在用户机器能录到系统声音（wav 文件非静音）
- [ ] 转写脚本输出中文带时间戳文本
- [ ] 笔记.md 七模块齐全、思维导图在开头、frontmatter 完整
- [ ] 总览画板 Dataview 能列出新笔记
