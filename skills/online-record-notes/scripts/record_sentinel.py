# -*- coding: utf-8 -*-
"""录音哨兵（cron 每 1 分钟）：保活「高频看门狗」，由看门狗负责 5 秒级拉起录音
规则：
  - stop.flag 存在（用户已停止录音）→ 输出为空，哨兵完全安静
  - 看门狗进程活着 → 输出为空（静默）
  - 看门狗死了 → 重启看门狗（看门狗会再拉起录音）+ 输出通知文本
  - 兜底：看门狗活着但录音进程也没了（看门狗自身异常）→ 直接拉起录音
"""
import os
import pathlib
import subprocess
import sys
import time

# ===== 配置区（按你的机器修改，或用环境变量覆盖，优先级：环境变量 > 默认值）=====
# 录音输出根目录（每节课一个子文件夹：<RECORD_BASE>/YYYY-MM-DD 课程名/录音/）
RECORD_BASE = os.environ.get("RECORD_BASE", r"D:\ai recording")
# 装有 pyaudiowpatch 的 python 解释器（录音依赖此库）
PYTHON = os.environ.get(
    "RECORD_PYTHON",
    r"C:\Users\84583\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe",
)
# ==============================================================

# 相对定位：watch_dog.py 与本脚本同目录
WATCHDOG_SCRIPT = str(pathlib.Path(__file__).resolve().parent / "watch_dog.py")
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def find_latest_record_dir():
    candidates = []
    for d in pathlib.Path(RECORD_BASE).glob("*"):
        rec = d / "录音"
        if rec.exists():
            candidates.append((rec.stat().st_mtime, rec))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def find_pids(pattern):
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         f"Where-Object {{ $_.CommandLine -match '{pattern}' }} | "
         "Select-Object -ExpandProperty ProcessId"],
        capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, timeout=30)
    return [int(x) for x in ps.stdout.split() if x.strip().isdigit()]


def main():
    record_dir = find_latest_record_dir()
    if record_dir is None:
        print("⚠️ 录音哨兵：D:\\ai recording 下没有找到录音目录")
        return

    stop_flag = record_dir / "stop.flag"
    if stop_flag.exists():
        return  # 录音已停止，安静

    watchdog_pids = find_pids(r"watch_dog\.py")
    if not watchdog_pids:
        # 看门狗死了 → 重启 + 通知
        subprocess.run([PYTHON, WATCHDOG_SCRIPT],
                       capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=30)
        print(f"⚠️ 录音看门狗已停止，已自动重启！输出目录：{record_dir}")
    else:
        # 看门狗活着；兜底：确认录音进程也在（看门狗可能在启动瞬间）
        record_pids = find_pids(r"record\.py")
        if not record_pids:
            subprocess.run([PYTHON, WATCHDOG_SCRIPT],
                           capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=30)
            print(f"⚠️ 录音进程异常，看门狗已重新拉起：{record_dir}")
        # 正常：静默


if __name__ == "__main__":
    main()
