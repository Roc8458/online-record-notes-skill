# -*- coding: utf-8 -*-
"""faster-whisper 转写脚本
用法:
  python transcribe.py <音频文件> <输出md>          # 单个 wav/m4a/mp3
  python transcribe.py <录音目录> <输出md>          # 目录含 seg_*.wav（record.py 输出），自动按序合并
模型: D:/hf-whisper/faster-whisper-large-v3（int8，CUDA）
"""
import ctypes
import os
import pathlib
import site
import sys
import time
import wave

# ctranslate2 4.8+ 不含 CUDA 库，pip 装的 nvidia 包 DLL 在 site-packages/nvidia/*/bin。
# Windows 上 ctranslate2 运行时动态 LoadLibrary 不认 add_dll_directory，
# 必须 add_dll_directory + ctypes 预加载（同名 DLL 已加载则后续 LoadLibrary 直接复用）。
for _sp in site.getsitepackages():
    for _sub in ["cublas", "cudnn"]:
        _d = pathlib.Path(_sp) / "nvidia" / _sub / "bin"
        if _d.exists():
            os.add_dll_directory(str(_d))
for _dll in ["cublas64_12.dll", "cudnn64_9.dll"]:
    try:
        ctypes.WinDLL(_dll)
        print(f"PRELOADED: {_dll}", flush=True)
    except Exception as _e:
        print(f"PRELOAD_WARN: {_dll} -> {_e}", flush=True)

import numpy as np
from faster_whisper import WhisperModel

MODEL_PATH = r"D:/hf-whisper/faster-whisper-large-v3"


def fmt(sec):
    sec = int(sec)
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def merge_segments(seg_dir):
    """按文件名序号读 seg_*.wav 合并成完整 pcm 数组"""
    segs = sorted(pathlib.Path(seg_dir).glob("seg_*.wav"))
    if not segs:
        raise FileNotFoundError(f"{seg_dir} 下没有 seg_*.wav 文件")
    parts, sr = [], None
    for p in segs:
        with wave.open(str(p), "rb") as w:
            if sr is None:
                sr = w.getframerate()
            assert w.getframerate() == sr and w.getsampwidth() == 2 and w.getnchannels() == 1
            parts.append(np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16))
    data = np.concatenate(parts)
    total_sec = len(data) / sr
    print(f"合并 {len(segs)} 段 -> 总时长 {total_sec/60:.1f} 分钟", flush=True)
    # 写临时完整 wav 供 faster-whisper 读取
    tmp = pathlib.Path(seg_dir) / "_merged.wav"
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return tmp


def main(src, out_path):
    t0 = time.time()
    src_path = pathlib.Path(src)
    if src_path.is_dir():
        audio = merge_segments(src_path)
    else:
        audio = str(src_path)

    print(f"LOADING model from {MODEL_PATH} ...", flush=True)
    model = WhisperModel(MODEL_PATH, device="cuda", compute_type="int8")
    print(f"loaded in {time.time()-t0:.1f}s | transcribing {audio} ...", flush=True)

    segments, info = model.transcribe(str(audio), language="zh", vad_filter=True, beam_size=5)

    lines = []
    for seg in segments:
        ts = fmt(seg.start)
        lines.append(f"[{ts}] {seg.text.strip()}")

    header = (
        f"# 原始记录\n\n"
        f"- 音频：{src}\n"
        f"- 时长：{fmt(info.duration)}\n"
        f"- 转写模型：faster-whisper-large-v3（int8）\n\n"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + "\n\n".join(lines))

    print(f"DONE: {len(lines)} 段 | 耗时 {time.time()-t0:.1f}s -> {out_path}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
