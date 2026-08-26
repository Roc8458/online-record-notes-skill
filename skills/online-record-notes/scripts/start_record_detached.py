# -*- coding: utf-8 -*-
"""以独立进程方式启动录音（脱离 Hermes 进程管理，防止被误杀/清理）
用法: python start_record_detached.py <输出目录>
  - 子进程 DETACHED 无窗口运行，父进程退出不影响它
  - 日志追加到 <输出目录>/record.log（供哨兵/排障查看）
  - 停止: 在输出目录创建 stop.flag（record.py 自己轮询，不依赖任何管理进程）
"""
import pathlib
import subprocess
import sys


def main(out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    script = pathlib.Path(__file__).resolve().parent / "record.py"
    log_path = out_dir / "record.log"
    log = open(log_path, "a", encoding="utf-8", errors="replace")
    log.write("\n===== START detached record at %s =====\n" % __import__("datetime").datetime.now())
    log.flush()
    p = subprocess.Popen(
        [sys.executable, "-u", str(script), str(out_dir)],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        stdout=log,
        stderr=subprocess.STDOUT,
        close_fds=True,
    )
    print(f"STARTED pid={p.pid} -> {out_dir}")
    print(f"LOG: {log_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
