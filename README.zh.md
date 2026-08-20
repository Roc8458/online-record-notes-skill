# 网课笔记 · Online Record Notes

一个 AI Agent skill：记录电脑正在播放的网课（系统声音）→ 本地 Whisper 转写 → 生成七模块结构化笔记存入 Obsidian。**音频全程不出电脑。**

v1.1.0 新功能：笔记按内容打标签 → 引用到 Obsidian 八大类文件夹 → 可选联动 LLM Wiki（Karpathy 式概念卡知识库），把网课从「一次性记录」变成「长期可查询的知识」。

## 效果预览

每节网课自动生成一个项目文件夹：

```
Online笔记/
├── 📊 网课总览.md                ← 总画板（Dataview 自动汇总所有课程，新的在前）
└── 2026-08-14 深度学习第3讲/       ← 每课一个项目
    ├── 笔记.md                   ← 开头是思维导图（手绘风）
    ├── 思维导图.excalidraw.md
    ├── 原始记录.md               ← 完整转写稿（带时间戳）
    └── 录音/                     ← 原始录音分段
```

> 默认文件夹叫「Online笔记」（不是「网课笔记」）；如果你已有自己的网课文件夹约定，跟随你的约定即可。

笔记包含七个模块：

| 模块 | 内容 |
| --- | --- |
| 🗺️ 思维导图 | 手绘风知识导图（Excalidraw，可编辑） |
| 📌 一句话总结 | 这节课讲了什么 |
| 🧠 核心内容 | 知识点提炼 |
| 📚 智能章节 | 按知识结构分章 + 时间戳 |
| 🎯 重点结论 | 核心观点/考点 |
| 💎 金句时刻 | 老师原话摘录 |
| 📜 原始记录 | 完整逐字稿 |

示例见 [examples/](examples/)（真实网课片段实录）。

## 工作原理

```
网课播放（电脑声卡）
    ↓ sounddevice WASAPI loopback 录制系统声音
录音分段（每 60 秒落盘，防丢）
    ↓ faster-whisper large-v3（int8，GPU 加速）
带时间戳逐字稿
    ↓ Agent 按 SKILL.md 规则整理
七模块笔记 + 思维导图 → Obsidian
```

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/Roc8458/online-record-notes-skill.git
```

### 2. 安装 skill 到你的 Agent

- **Hermes**：把 `skills/online-record-notes` 复制到 Hermes skills 目录（`hermes` 的 skills 文件夹下）
- **Codex**：复制到 `~/.codex/skills/`
- **Claude Code**：复制到 `~/.claude/skills/`
- 或者直接跟你的 Agent 说：*"帮我安装 https://github.com/Roc8458/online-record-notes-skill 里的 skill"*

### 3. 安装 Python 依赖

```bash
pip install -r skills/online-record-notes/scripts/requirements.txt
```

### 4. 下载转写模型（3GB，一次性）

large-v3 是 Whisper 系列最强型号（中文准确率接近商用）。国内建议走 hf-mirror 镜像（直连稳定，无需 VPN）：

```python
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_DISABLE_XET"] = "1"  # 镜像站不支持 Xet 协议，必须禁用
from huggingface_hub import snapshot_download
snapshot_download("Systran/faster-whisper-large-v3",
                  local_dir="D:/hf-whisper/faster-whisper-large-v3")
```

改模型位置的话，同步改 `scripts/transcribe.py` 顶部的 `MODEL_PATH`。

### 5. 确认 Obsidian

- 笔记存进你的 Obsidian vault 的 `Online笔记/` 文件夹（SKILL.md「目录约定」里确认路径）
- 总览画板需要 **Dataview 插件**
- 思维导图需要 **Excalidraw 插件**

## 使用

1. 看网课前说：**「开始记录网课」**（Agent 会问课程名，然后后台录音）
2. 看完课说：**「停止并整理」**
3. 等转写（1 小时课约 25-40 分钟，后台跑）
4. 笔记自动出现在 Obsidian，总览画板自动更新
5. **首次使用时 Agent 会问你是否启用归档联动**（八大类入口 + LLM Wiki）：同意后每节网课会按内容打标签、引用进你的八大类文件夹，并同步知识到 LLM Wiki；随时可以说「关掉联动」取消

## 归档联动（v1.1.0）

| 功能 | 说明 |
| --- | --- |
| 内容标签 | 笔记 tags 自动加 2~5 个主题标签（如 AI/就业/FDE） |
| 八大类入口 | 在八大类文件夹（社会/技能/思维…）创建 embed 引用笔记，单一副本不复制 |
| LLM Wiki | 更新/新建概念卡，互链 + index/log 同步（需 WIKI_PATH 或 vault/wiki/） |
| 同意机制 | 首次询问，`.note-consent` 标记文件开关 |

## 硬件要求

- Windows 10/11
- NVIDIA 显卡（实测 RTX 4060 Laptop 8GB，CUDA 12）
- 约 4GB 磁盘（模型 3GB + CUDA 库 1.3GB）
- 无 NVIDIA 显卡也可跑 CPU 模式（改 transcribe.py 的 `device="cpu"`，速度慢约 10 倍）

## License

MIT © 2026 Roc Wan

## English

[English documentation: README.md](README.md)
