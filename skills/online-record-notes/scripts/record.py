# -*- coding: utf-8 -*-
"""录制系统声音（网课录音）—— pyaudiowpatch WASAPI loopback
用法: python record.py <输出目录>
  - 输出目录下每 60 秒写一段 seg_0001.wav, seg_0002.wav ...（16kHz 单声道 16bit）
  - 停止方式：在输出目录创建 stop.flag 文件（脚本每 0.5 秒轮询），优雅保存后退出
  - 退出时写 manifest.json（段数/总时长/设备名）
防丢设计：即使进程被杀，已完成的 seg 段完好，transcribe.py 支持直接读段文件转写。

录音原理（2026-08-27 实测）：
  - sounddevice(WDM-KS/WASAPI) 在本机已失效（PaErrorCode -9996），改用 pyaudiowpatch 的 WASAPI loopback
  - WASAPI loopback 只在系统有声音输出时产生数据；静音时段无回调，内容自然跳过静音
  - 因此录音时电脑必须正在播放声音（网课）才有内容
"""
import json
import pathlib
import re
import sys
import time
import wave

import numpy as np
import pyaudiowpatch as pyaudio

OUT_SR = 16000  # whisper 标准：16kHz 单声道
SEG_SECONDS = 60  # 每段时长（秒）


def find_loopback():
    """找 WASAPI 默认输出设备的 loopback 对应设备（录系统声音）"""
    p = pyaudio.PyAudio()
    try:
        wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi["defaultOutputDevice"])
        if not default_speakers.get("isLoopbackDevice"):
            for candidate in p.get_loopback_device_info_generator():
                if default_speakers["name"] in candidate["name"]:
                    default_speakers = candidate
                    break
            else:
                raise RuntimeError(f"找不到 {default_speakers['name']} 的 loopback 设备")
        return p, default_speakers
    except Exception:
        p.terminate()
        raise


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

    p, dev = find_loopback()
    src_sr = int(dev["defaultSampleRate"])
    channels = dev["maxInputChannels"]
    print(f"DEVICE: [{dev['index']}] {dev['name']} | {src_sr}Hz x{channels}ch", flush=True)
    print(f"OUT_DIR: {out_dir} | 每 {SEG_SECONDS}s 落盘一段 | 停止=在该目录创建 stop.flag", flush=True)

    buf = []
    # 启动时继承已有 seg 编号：进程重启后继续往下写，不覆盖旧文件（文件名顺序=时间顺序）
    max_idx = 0
    for f in out_dir.glob("seg_*.wav"):
        m = re.match(r"seg_(\d+)\.wav", f.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    state = {"seg_idx": max_idx, "total_frames": 0, "last_flush": time.time(), "callbacks": 0,
             "content_seconds": 0.0}

    def flush(buff):
        if not buff:
            return
        data = np.concatenate(buff)
        mono = downmix_to_16k(data, src_sr, channels)
        pcm = (np.clip(mono, -1, 1) * 32767).astype(np.int16)
        state["seg_idx"] += 1
        write_wav(out_dir / f"seg_{state['seg_idx']:04d}.wav", pcm)
        state["total_frames"] += len(pcm)
        state["content_seconds"] = 0.0
        print(f"SEG_SAVED: seg_{state['seg_idx']:04d}.wav ({len(pcm)/OUT_SR:.0f}s)", flush=True)

    def callback(in_data, frame_count, time_info, status):
        arr = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            arr = arr.reshape(-1, channels)
        else:
            arr = arr.reshape(-1, 1)
        buf.append(arr)
        state["callbacks"] += 1
        state["content_seconds"] += frame_count / src_sr
        if state["content_seconds"] >= SEG_SECONDS:
            flush(buf)
            buf.clear()
        return (None, pyaudio.paContinue)

    print("RECORDING: 开始录音。停止方式：在输出目录创建 stop.flag 文件", flush=True)
    stream = None
    try:
        stream = p.open(format=pyaudio.paInt16, channels=channels, rate=src_sr,
                        input=True, input_device_index=dev["index"],
                        frames_per_buffer=1024,
                        stream_callback=callback)
        last_hb = time.time()
        while not stop_flag.exists():
            time.sleep(0.5)
            if time.time() - last_hb >= 10:
                last_hb = time.time()
                print(f"HEARTBEAT: callbacks={state['callbacks']} content_sec={state['content_seconds']:.0f} segs={state['seg_idx']}", flush=True)
    finally:
        try:
            if stream is not None:
                stream.stop_stream()
                stream.close()
        except Exception:
            pass
        p.terminate()

    flush(buf)
    dur = state["total_frames"] / OUT_SR
    manifest = {
        "device": dev["name"],
        "device_index": dev["index"],
        "segments": state["seg_idx"],
        "total_seconds": round(dur, 1),
        "sample_rate": OUT_SR,
        "channels": 1,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE: {state['seg_idx']} 段，共 {dur/60:.1f} 分钟 -> {out_dir}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "录音")
