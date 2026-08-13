# -*- coding: utf-8 -*-
"""录制系统声音（网课录音）—— 实测有效设备：Realtek HD Audio output with SST（WDM-KS loopback）
用法: python record.py <输出目录>
  - 输出目录下每 60 秒写一段 seg_0001.wav, seg_0002.wav ...（16kHz 单声道 16bit）
  - 停止方式：在输出目录创建 stop.flag 文件（脚本每 0.5 秒轮询），优雅保存后退出
  - 退出时写 manifest.json（段数/总时长/设备名）
防丢设计：即使进程被杀，已完成的 seg 段完好，transcribe.py 支持直接读段文件转写。
"""
import json
import pathlib
import sys
import time
import wave

import numpy as np
import sounddevice as sd

OUT_SR = 16000  # whisper 标准：16kHz 单声道
SEG_SECONDS = 60  # 每段时长（秒）

# 实测有效设备的名称关键字（按优先级，2026-08 探针实测：RMS 0.55，THX/立体声混音均无效）
DEVICE_KEYWORDS = [
    "Realtek HD Audio output with SST",
    "电脑扬声器",
]


def find_device():
    """按名字匹配 loopback 设备（索引每次开机会变，只认名字）"""
    devices = sd.query_devices()
    for kw in DEVICE_KEYWORDS:
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0 and kw.lower() in d["name"].lower():
                return i, d
    # 兜底：任何带 output/speaker 且有输入通道的 KS 设备（排除 THX——实测静音）
    for i, d in enumerate(devices):
        n = d["name"].lower()
        if (
            d["max_input_channels"] > 0
            and ("output" in n or "speaker" in n)
            and "thx" not in n
        ):
            return i, d
    return None, None


def downmix_to_16k(data, src_sr, channels):
    if channels > 1:
        data = data.mean(axis=1)
    if src_sr != OUT_SR:
        n = int(len(data) * OUT_SR / src_sr)
        data = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(data)), data)
    return data.astype(np.float32)


def write_wav(path, pcm_int16):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(OUT_SR)
        w.writeframes(pcm_int16.tobytes())


def main(out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stop_flag = out_dir / "stop.flag"
    stop_flag.unlink(missing_ok=True)

    idx, dev = find_device()
    if idx is None:
        print("NO_DEVICE: 找不到 loopback 录音设备", flush=True)
        sys.exit(1)
    src_sr = int(dev["default_samplerate"])
    channels = dev["max_input_channels"]
    print(f"DEVICE: [{idx}] {dev['name']} | {src_sr}Hz x{channels}ch", flush=True)
    print(f"OUT_DIR: {out_dir} | 每 {SEG_SECONDS}s 落盘一段 | 停止=在该目录创建 stop.flag", flush=True)

    buf = []
    state = {"seg_idx": 0, "total_frames": 0, "last_flush": time.time()}

    def flush(buf):
        if not buf:
            return
        data = np.concatenate(buf)
        mono = downmix_to_16k(data, src_sr, channels)
        pcm = (np.clip(mono, -1, 1) * 32767).astype(np.int16)
        state["seg_idx"] += 1
        write_wav(out_dir / f"seg_{state['seg_idx']:04d}.wav", pcm)
        state["total_frames"] += len(pcm)
        print(f"SEG_SAVED: seg_{state['seg_idx']:04d}.wav ({len(pcm)/OUT_SR:.0f}s)", flush=True)

    def callback(indata, frames, t, status):
        buf.append(indata.copy())
        if time.time() - state["last_flush"] >= SEG_SECONDS:
            flush(buf)
            buf.clear()
            state["last_flush"] = time.time()

    print("RECORDING: 开始录音。停止方式：在输出目录创建 stop.flag 文件", flush=True)
    try:
        with sd.InputStream(
            device=idx, samplerate=src_sr, channels=channels,
            dtype="float32", callback=callback,
        ):
            while not stop_flag.exists():
                time.sleep(0.5)
    finally:
        pass

    flush(buf)
    dur = state["total_frames"] / OUT_SR
    manifest = {
        "device": dev["name"],
        "device_index": idx,
        "segments": state["seg_idx"],
        "total_seconds": round(dur, 1),
        "sample_rate": OUT_SR,
        "channels": 1,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE: {state['seg_idx']} 段，共 {dur/60:.1f} 分钟 -> {out_dir}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "录音")
