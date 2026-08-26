---
name: online-record-notes
description: Use when 用户要记录网课整理成笔记。录音转写后生成七模块笔记存 Obsidian，可选联动八大类归档 + LLM Wiki。
version: 1.2.0
author: Roc Wan
license: MIT
metadata:
  hermes:
    tags: [网课, 笔记, 录音, 转写, whisper, obsidian]
---

# 网课笔记 · Online Record Notes

记录电脑正在播放的网课（系统声音）→ 本地转写 → 七模块结构化笔记 → 存进 Obsidian 并更新总览画板。全程本地处理，音频不出电脑。

- v1.1.0 新增：笔记内容打标签 + 按内容引用到 Obsidian 八大类 + 可选 LLM Wiki 联动（见「归档联动」）。
- v1.2.0 新增：录音引擎换 **pyaudiowpatch（WASAPI loopback）**（sounddevice/WDM-KS 在部分系统更新后失效，报 `PaErrorCode -9996`）；录音输出改到 **D 盘**（`RECORD_BASE`，不占系统盘）；新增 **独立进程启动**（防 Agent 后台进程误杀）+ **高频看门狗**（5 秒级自动重启）+ **cron 哨兵**（1 分钟保活看门狗）。

## 触发词

- 「开始记录网课」「记录网课」「开始录音」→ 启动后台录音
- 「停止记录，整理成笔记」「停止并整理」「结束网课记录」→ 停止录音 + 转写 + 整理 + 存笔记

## 配置区（安装后必读，见 README.md）

| 配置项 | 位置 | 默认值 |
| --- | --- | --- |
| Obsidian vault 路径 | 下方「目录约定」 | `<vault>`（首次使用先向用户确认实际路径，如 `C:\Users\<名>\Documents\MyVault`） |
| 录音输出根目录 | `watch_dog.py` / `record_sentinel.py` 顶部配置区，或环境变量 `RECORD_BASE` | `D:\ai recording`（每节课一个子文件夹：`<RECORD_BASE>/YYYY-MM-DD 课程名/录音/`） |
| 录音用 Python 解释器 | `watch_dog.py` / `record_sentinel.py` 顶部配置区，或环境变量 `RECORD_PYTHON` | 装有 pyaudiowpatch 的解释器（如 Hermes venv 的 python.exe） |
| 转写模型路径 | `scripts/transcribe.py` 顶部 `MODEL_PATH` | `D:/hf-whisper/faster-whisper-large-v3` |
| Python 依赖 | `scripts/requirements.txt` | 安装命令见 README |

> 路径配置原则：脚本顶部有醒目的「配置区」常量，默认值是作者机器的实际路径；换机器/换路径时改配置区或设环境变量即可，**不要改业务代码**。

## 目录约定

- Obsidian vault：`<vault>`（先向用户确认实际 vault 路径，不要假设）
- 笔记根：`<vault>\Online笔记\`（⚠️ 默认「Online笔记」文件夹，不是「网课笔记」；用户已有其他约定时跟随用户）
- 总览画板：`<vault>\Online笔记\📊 网课总览.md`
- **录音文件放 RECORD_BASE**（默认 `D:\ai recording`，用户要求不占 C 盘）：`<RECORD_BASE>\YYYY-MM-DD 课程名\录音\`（seg_0001.wav 每 60 秒一段 + manifest.json）
- **笔记文件放 vault**：`Online笔记\YYYY-MM-DD 课程名\`，内含：
  - `原始记录.md` — 转写逐字稿（带时间戳）
  - `笔记.md` — 七模块结构化笔记（思维导图放在最开头）
  - `思维导图.excalidraw.md` — 手绘风思维导图（Obsidian Excalidraw 新格式）

## 录音流程

1. 用户说「开始记录网课」时：
   - 先问课程名（用于文件夹命名），如「深度学习第3讲」
   - 创建录音目录：`<RECORD_BASE>\YYYY-MM-DD 课程名\录音\`（📌 录音不占 C 盘）
   - **用独立进程启动录音**（不要用 terminal background 直接跑 record.py——Agent 后台进程可能被误杀）：
     `python <skill_dir>/scripts/start_record_detached.py "<RECORD_BASE>/YYYY-MM-DD 课程名/录音"`
   - 启动「高频看门狗」：`python <skill_dir>/scripts/watch_dog.py`（每 5 秒检查录音，挂了自动重启）
   - 有 Hermes/cron 时，建 cron 哨兵跑 `scripts/record_sentinel.py`（every 1m, no_agent）保活看门狗
   - 告知用户「开始录音了，看完课说『停止并整理』」
2. 录音脚本：`scripts/record.py`（pyaudiowpatch WASAPI loopback 录系统声音，输出 wav）
   - 依赖：`pip install pyaudiowpatch`（sounddevice 的 WDM-KS/WASAPI 在部分系统已失效，PaErrorCode -9996，勿回退）
   - 日志写到 `<录音目录>/record.log`（心跳每 10s：callbacks/content_sec/segs），排障看这里
   - 脚本自动找 WASAPI 默认输出设备的 loopback（设备名形如「扬声器 (Realtek(R) Audio) [Loopback]」）
   - ⚠️ WASAPI loopback 只在系统有声音输出时产生数据：静音时段无回调、内容自然跳过；开始录音后要确认课程声音在播放
   - 分段按「内容时长 60s」落盘（静音不拖延）；**启动时自动继承已有 seg 编号**（重启不覆盖旧文件，文件名顺序=时间顺序）
3. 保活体系（防中断漏录）：
   - **看门狗** `watch_dog.py`：每 5 秒检查录音进程，死了立即拉起（漏录窗口 ~5-10 秒）；检测到 stop.flag（用户停止）自动退出
   - **哨兵** `record_sentinel.py`：cron 每 1 分钟检查看门狗，死了重启 + 通知；stop.flag 存在时完全安静

## 转写流程

1. 用户说「停止记录」时：**在录音输出目录创建 `stop.flag` 文件**（用 write_file 写一个空文件即可），脚本检测到后优雅保存退出
   - 录音脚本每 60 秒落盘一段 `seg_XXXX.wav`，即使异常被杀，已落盘的分段完好（转写脚本直接读目录合并）
   - 注意：部分 Agent 环境后台进程 stdin 不可用，不要用 process write/submit 停录音；用 stop.flag 文件
2. 运行转写：`python <skill_dir>/scripts/transcribe.py <录音目录> <原始记录.md>`（目录含 seg_*.wav，自动合并）
   - faster-whisper **large-v3（int8）** 模型，中文，输出带时间戳文本
   - 1 小时音频约 25-40 分钟，用后台任务跑，完成通知后再继续
3. 转写完成后读入 `原始记录.md` 全文

## 七模块笔记规则（笔记.md）

> 笔记生成后按「归档联动」章节做：内容打标签 + 八大类入口 + wiki 联动（启用后）。

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
- 笔记.md 的 frontmatter：**tags 不能只有 `[网课笔记]`，要按内容加 2~5 个主题标签**（领域 + 主题词，如 `AI`、`就业`、`FDE`、`数据标注`、`算力部署`），便于总览筛选和 wiki 分类：

```yaml
---
course: <课程名>
date: <YYYY-MM-DD>
duration: <分钟数>
tags: [网课笔记, <内容标签1>, <内容标签2>, ...]
summary: <一句话总结>
---
```

## Obsidian 落盘

1. 创建课程文件夹，写入 `原始记录.md`、`笔记.md`、`思维导图.excalidraw.md`（`录音\` 分段目录已由录音脚本写入 RECORD_BASE 下）
2. **更新总览画板** `📊 网课总览.md`：
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
3. **打内容标签**：`笔记.md` frontmatter 的 tags 按内容加主题标签（见「七模块笔记规则」）
4. **八大类入口（引用）**：按内容主题把笔记引用到 Obsidian 八大类对应位置（见「归档联动」）
5. **Wiki 联动**：如果已启用，按「归档联动」更新 LLM Wiki
6. 完成后告知用户：笔记路径 + 一句总结 + 「已更新总览画板」

## 归档联动（可选扩展：八大类入口 + LLM Wiki）

把网课笔记从「一次性记录」变成「长期可查询的知识」：内容打标签 → 引用进 Obsidian 八大类 → 同步 LLM Wiki。

### C0. 首次使用同意机制（必须）

**第一次**使用本 skill 时，先问用户：

> 「是否启用 Obsidian 归档联动？启用后：每节网课笔记会按内容打标签、引用到你的八大类文件夹（社会/技能/思维…），并把知识同步进你的 LLM Wiki（Karpathy 式概念卡知识库）。同意吗？」

- **同意** → 在 vault 写同意标记文件 `<vault>/.note-consent`（内容：日期 + 用户声明），以后不再问
- **拒绝** → 不写标记，只做基础落盘（Online笔记 + 画板），不做八大类入口和 wiki 联动
- 用户说「启用联动 / 关掉联动」可随时开关（开关 = 创建/删除 `.note-consent`）

### C1. 内容标签

- 标签 2~5 个，中文为主：领域（AI/编程/经济…）+ 主题词（就业/岗位/FDE…）+ 形式（网课/播客/对话）
- 写进 `笔记.md` frontmatter `tags`，同时用于总览筛选

### C2. 八大类入口（Obsidian embed 引用）

- 按内容主题把笔记引用到用户的八大类文件夹（若用户有这套体系；没有则跳过此步）
- 在目标文件夹创建入口笔记（文件名带日期，如 `2026-08-21 AI时代三大爆火岗位（网课）.md`）
- 内容用 **Obsidian embed 引用**：`![[Online笔记/课程文件夹/笔记]]`——单一副本，不改动原笔记
- 入口笔记 frontmatter 带 tags + `source: Online笔记/课程文件夹/笔记.md`
- 一节网课常横跨 2~4 个类（例：就业→社会/职场规则/AI与就业、行业→社会/商业认知/AI行业分析、岗位能力→技能/专业能力/对应文件夹）
- 若用户没有八大类体系，可跳过或询问用户想怎么分类

### C3. LLM Wiki 联动

- 定位 wiki：环境变量 `WIKI_PATH` → 默认 `<vault>/wiki/`
- **先查重**：读 `<wiki>/index.md`，内容与已有页重叠 → 更新旧页（bump `updated`、追加 `sources`），**不新建重复页**
- 没有覆盖的实体/概念 → 新建概念页（frontmatter 完整、至少 2 出链、中文大白话）
- 更新 `index.md` + `log.md`
- 只新增不改动原笔记；涉及 10+ 页面的批量操作先征求用户同意

### C4. 验证

- 跑 `check_wikilinks.py`（obsidian-llm-wiki 技能自带）检查断链：0 真实断链才算完
- 入口笔记的 embed 引用会被脚本按 basename 正确识别，附件引用（PDF/PNG）不算断链

## 常见坑

1. **录音录不到声音**：① 先确认电脑在播放声音——WASAPI loopback 静音时不产生数据（callback 不触发，content_sec 不涨）；② 确认 pyaudiowpatch 已安装（sounddevice 的 WDM-KS 打开报 PaErrorCode -9996，已弃用，别再试回 sounddevice）；③ 看 record.log 的 DEVICE 行确认找到「[Loopback]」设备。
2. **record.py 崩溃 AxisError: axis 1 out of bounds**：pyaudiowpatch callback 的 in_data 是一维字节流，必须 `np.frombuffer(...).reshape(-1, channels)` 再 mean(axis=1)，当前脚本已内置。
3. **录音进程被误杀/中断**：不要用 terminal background=true 跑录音（Agent 会偶发清理后台进程）；必须用 start_record_detached.py 独立进程 + watch_dog.py 看门狗。若已用独立进程仍中断，查 record.log 尾部 + 哨兵 cron 会自动重启并通知。
4. **用户中途换课**：新课程要重新说「开始记录网课」，一节课一个文件夹。
5. **转写很慢别催**：后台任务跑，完成通知后再继续，别中途 poll。
6. **m4a 不直接转**：录音脚本输出 wav，转写脚本也支持 m4a/mp3（faster-whisper 内部解码），用户如果自己录了 m4a 也能用。
7. **总览画板不显示**：检查笔记 frontmatter 的 tags 含「网课笔记」，且文件在「Online笔记」文件夹下（Dataview FROM 路径匹配）。
8. **传路径必须用 Windows 原生格式**：`C:\Users\...` 或 `C:/Users/...`，不要用 bash 的 `/c/Users/...`（MSYS 风格，PyAV 不认，会 FileNotFoundError）。
9. **报 `cublas64_12.dll not found`**：ctranslate2 4.8+ 不含 CUDA 库。两步解决：① `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`；② 脚本里必须 `os.add_dll_directory(site-packages/nvidia/*/bin)` + `ctypes.WinDLL("cublas64_12.dll")` 预加载（仅 add_dll_directory 无效，ctranslate2 运行时 LoadLibrary 不认；预加载后同名 DLL 直接复用）。transcribe.py 已内置此逻辑。
10. **uv venv 的 python 是「转发器」**：Hermes/uv 创建的 venv，其 python.exe 启动时会派生一个真实解释器子进程（同秒两个 PID 属正常，不是重复进程）。**Stop-Process 杀子进程可能连坐父进程**，清理时要按进程对一起处理；哨兵/看门狗必须用配置区写死的 PYTHON（装有 pyaudiowpatch 的解释器），不要用 sys.executable 传递（cron 可能用别的 python 跑）。

## 验证清单

- [ ] 录音脚本能录到系统声音（wav 文件非静音；静音时 callbacks 不涨属正常）
- [ ] 录音以独立进程运行，看门狗 5 秒级自愈，哨兵 1 分钟保活
- [ ] 录音文件落在 RECORD_BASE（不占系统盘），seg 编号连续不覆盖
- [ ] 转写脚本输出中文带时间戳文本
- [ ] 笔记.md 七模块齐全、思维导图在开头、frontmatter 完整
- [ ] frontmatter tags 含内容标签（不只 [网课笔记]）
- [ ] 总览画板 Dataview 能列出新笔记（Online笔记 路径）
- [ ] （启用联动后）八大类入口笔记能正常 embed 显示原笔记
- [ ] （启用联动后）wiki 页更新/新建完成，index/log 同步，断链检查 0 真实断链
