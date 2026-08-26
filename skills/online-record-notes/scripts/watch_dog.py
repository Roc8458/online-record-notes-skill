# -*- coding: utf-8 -*-
"""录音高频看门狗：每 5 秒检查录音进程，挂了立即重启（漏录窗口 ~5-10 秒）
用法:
  python watch_dog.py            # 以独立守护进程启动，立即返回
  python watch_dog.py --daemon   # 守护模式（内部用，勿手输）
停止录音后（stop.flag 出现）看门狗自动退出；由 cron 哨兵 record_sentinel.py 保活本看门狗。
"""
import os
import pathlib
import subprocess
import sys
import time

# ===== 配置区（按你的机器修改，或用环境变量覆盖，优先级：环境变量 > 默认值）=====
# 录音输出根目录（每节课一个子文件夹：<RECORD_BASE>/YYYY-MM-DD 课程名/录音/）
RECORD_BASE = os.environ.get("RECORD_BASE", r"D:\ai recording")
# 装有 pyaudiowpatch 的 python 解释器（录音依赖此库；cron 等其他环境可能用没有该库的 python）
PYTHON = os.environ.get(
    "RECORD_PYTHON",
    r"C:\Users\84583\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe",
)
# ==============================================================

# 相对定位：start_record_detached.py 与本脚本同目录
START_SCRIPT = str(pathlib.Path(__file__).resolve().parent / "start_record_detached.py")
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
CHECK_INTERVAL = 5  # 秒


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


def find_record_pids():
    ps = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -match 'record\\.py' } | "
         "Select-Object -ExpandProperty ProcessId"],
        capture_output=True, text=True, creationflags=CREATE_NO_WINDOW, timeout=20)
    return [int(x) for x in ps.stdout.split() if x.strip().isdigit()]


def restart(record_dir):
    subprocess.run([PYTHON, START_SCRIPT, str(record_dir)],
                   capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=30)


def log(msg, log_path):
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def main():
    while True:
        record_dir = find_latest_record_dir()
        if record_dir is not None:
            break
        time.sleep(30)  # 还没有课程目录，等

    stop_flag = record_dir / "stop.flag"
    log_path = record_dir / "watchdog.log"
    log("看门狗启动，每 5s 检查一次录音", log_path)
    while True:
        if stop_flag.exists():
            log("检测到 stop.flag，看门狗退出（录音已停止）", log_path)
            break
        if not find_record_pids():
            restart(record_dir)
            log("录音进程挂了，已重启", log_path)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        main()
    else:
        # 以独立守护进程启动自己，立即返回
        p = subprocess.Popen(
            [PYTHON, "-u", str(pathlib.Path(__file__).resolve()), "--daemon"],
            creationflags=CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        print(f"WATCHDOG STARTED pid={p.pid}")
