# Online Record Notes

An AI Agent skill that records online courses playing on your computer (system audio) → transcribes locally with Whisper → generates a seven-section structured note in Obsidian. **Audio never leaves your machine.**

v1.2.0 new: recording engine switched to **pyaudiowpatch (WASAPI loopback)** — sounddevice/WDM-KS broke on some systems (`PaErrorCode -9996`). Audio now lands on a configurable `RECORD_BASE` drive (default `D:\ai recording`, keeps your system drive free). Added detached-process launch (immune to agent background-process cleanup), a 5-second watchdog, and a 1-minute cron sentinel — recording self-heals within ~10s if it ever dies.

v1.1.0 new: content-based tagging → embed references into your Obsidian category folders → optional LLM Wiki sync (Karpathy-style concept cards). Turns each course from a one-off recording into long-term queryable knowledge.

## Preview

Each course becomes a self-contained project folder:

```
Online笔记/ (course notes root in your vault)
├── 📊 网课总览.md                ← dashboard (Dataview auto-aggregates all courses, newest first)
└── 2026-08-14 Deep Learning L3/   ← one folder per course
    ├── 笔记.md                   ← note with mind map at the top (hand-drawn)
    ├── 思维导图.excalidraw.md     ← editable mind map (Excalidraw)
    ├── 原始记录.md               ← full transcript with timestamps
    └── 录音/                     ← raw audio segments (stored under RECORD_BASE, default D:\ai recording, not the system drive)
```

> Default folder is named "Online笔记" (not "网课笔记"); if you already have your own course-notes convention, follow yours instead.

The note contains seven sections:

| Section | Content |
| --- | --- |
| 🗺️ Mind map | Hand-drawn knowledge map (Excalidraw, editable) |
| 📌 One-line summary | What this course is about |
| 🧠 Core content | Distilled knowledge points |
| 📚 Smart chapters | Chapters by knowledge structure + timestamps |
| 🎯 Key takeaways | Core conclusions / exam points |
| 💎 Quote moments | Verbatim quotes from the instructor |
| 📜 Raw transcript | Full transcript |

See [examples/](examples/) for a real output sample.

## How it works

```
Course playing on your PC (sound card)
    ↓ sounddevice WASAPI loopback records system audio
Segmented recordings (flushed to disk every 60s, crash-safe)
    ↓ faster-whisper large-v3 (int8, GPU accelerated)
Timestamped transcript
    ↓ Agent follows SKILL.md rules to structure it
Seven-section note + mind map → Obsidian
```

## Installation

### 1. Clone

```bash
git clone https://github.com/Roc8458/online-record-notes-skill.git
```

### 2. Install the skill into your Agent

- **Hermes**: copy `skills/online-record-notes` into Hermes' skills directory
- **Codex**: copy to `~/.codex/skills/`
- **Claude Code**: copy to `~/.claude/skills/`
- Or just tell your Agent: *"Install the skill from https://github.com/Roc8458/online-record-notes-skill"*

### 3. Install Python dependencies

```bash
pip install -r skills/online-record-notes/scripts/requirements.txt
```

### 4. Download the transcription model (3GB, one-time)

large-v3 is Whisper's strongest model (Chinese accuracy close to commercial services). Users in mainland China should use the hf-mirror (direct connection, no VPN needed):

```python
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_DISABLE_XET"] = "1"  # mirror doesn't support Xet protocol
from huggingface_hub import snapshot_download
snapshot_download("Systran/faster-whisper-large-v3",
                  local_dir="D:/hf-whisper/faster-whisper-large-v3")
```

If you change the model location, update `MODEL_PATH` at the top of `scripts/transcribe.py`.

### 5. Obsidian setup

- Notes go into `Online笔记/` folder inside your Obsidian vault (confirm the vault path in SKILL.md's directory conventions)
- Dashboard requires the **Dataview** plugin
- Mind maps require the **Excalidraw** plugin

## Usage

1. Before the course starts, tell your Agent: **"Start recording the course"** (it asks for a course name, then records in the background)
2. After the course: **"Stop and organize"**
3. Wait for transcription (a 1-hour course takes ~25-40 min in the background)
4. Notes appear in Obsidian; the dashboard updates automatically
5. **On first use the Agent asks whether to enable archive linking** (category-folder entries + LLM Wiki): if you agree, each course gets content tags, embed references into your category folders, and knowledge synced to the LLM Wiki; say "disable linking" anytime to turn it off

## Archive linking (v1.1.0)

| Feature | Description |
| --- | --- |
| Content tags | Note tags get 2~5 topic tags automatically (e.g. AI/jobs/FDE) |
| Category entries | Embed-reference notes created in your category folders (social/skills/thinking…) — single copy, never duplicated |
| LLM Wiki | Update/create concept cards, interlink + index/log sync (needs WIKI_PATH or vault/wiki/) |
| Consent | Asked on first use; `.note-consent` marker file toggles it |

## Requirements

- Windows 10/11
- NVIDIA GPU (tested on RTX 4060 Laptop 8GB, CUDA 12)
- ~4GB disk (3GB model + 1.3GB CUDA libraries)
- No NVIDIA GPU? CPU mode works too (set `device="cpu"` in transcribe.py, ~10x slower)

## License

MIT © 2026 Roc Wan

## 中文说明

[中文文档请见 README.zh.md](README.zh.md)
