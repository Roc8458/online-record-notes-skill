"""
网课录制桌面卡片 - 真实调用录音功能
始终置顶 + 任务栏 + 最小化到任务栏
启动: python record_desktop.py [--auto-start]
"""
import tkinter as tk
import subprocess
import pathlib
import sys
import datetime
import traceback

# 配置
SKILL_DIR = pathlib.Path(__file__).resolve().parent
RECORD_BASE = pathlib.Path("D:/ai recording")
PYTHON = sys.executable
LOG_PATH = SKILL_DIR / "card_ui.log"


def log(msg):
    """所有动作写日志，方便排障"""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%H:%M:%S}] {msg}\n")
    except Exception:
        pass


def excepthook(tp, val, tb):
    log("EXCEPTION: " + "".join(traceback.format_exception(tp, val, tb)))


sys.excepthook = excepthook


class RecordCard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("网课录制")
        w, h = 280, 110
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sx - w - 20}+{sy - h - 80}")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)

        # 状态
        self.state = "idle"  # idle / recording / paused / stopped
        self.elapsed = 0
        self.timer_running = False
        self.out_dir = None

        # === 顶栏 ===
        header = tk.Frame(self.root, bg="#1e1e30", cursor="hand2")
        header.pack(fill="x")
        left = tk.Frame(header, bg="#1e1e30")
        left.pack(side="left", padx=10, pady=6)
        self.dot_c = tk.Canvas(left, width=8, height=8, bg="#1e1e30", highlightthickness=0)
        self.dot_c.pack(side="left", padx=(0, 5))
        self.dot = self.dot_c.create_oval(1, 1, 7, 7, fill="#555", outline="")
        self.lbl_status = tk.Label(left, text="就绪", fg="#888", bg="#1e1e30",
                                   font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(side="left")
        self.lbl_time = tk.Label(header, text="00:00", fg="#666", bg="#1e1e30",
                                 font=("Consolas", 11))
        self.lbl_time.pack(side="right", padx=10, pady=6)
        tk.Frame(self.root, bg="#2a2a3e", height=1).pack(fill="x")

        # === 按钮区 ===
        btns = tk.Frame(self.root, bg="#1a1a2e")
        btns.pack(fill="x", padx=10, pady=6)
        self.btn_start = tk.Button(btns, text="开始录制", fg="#fff", bg="#2563eb",
                                   activebackground="#1d4ed8", relief="flat", bd=0,
                                   font=("Segoe UI", 9), padx=12, pady=3,
                                   command=self.on_start)
        self.btn_start.pack(side="left", padx=(0, 4))
        self.btn_pause = tk.Button(btns, text="暂停", fg="#ccc", bg="#333",
                                   activebackground="#444", relief="flat", bd=0,
                                   font=("Segoe UI", 9), padx=12, pady=3,
                                   command=self.on_pause, state="disabled")
        self.btn_pause.pack(side="left", padx=(0, 4))
        self.btn_stop = tk.Button(btns, text="结束", fg="#ef4444", bg="#333",
                                  activebackground="#444", relief="flat", bd=0,
                                  font=("Segoe UI", 9), padx=12, pady=3,
                                  command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left")
        self.btn_min = tk.Button(btns, text="─", fg="#666", bg="#1a1a2e",
                                 activebackground="#333", relief="flat", bd=0,
                                 font=("Segoe UI", 9), padx=4, command=self.minimize)
        self.btn_min.pack(side="right")

        # === 底部状态 ===
        self.lbl_info = tk.Label(self.root, text="", fg="#666", bg="#1a1a2e",
                                 font=("Segoe UI", 8), anchor="w")
        self.lbl_info.pack(fill="x", padx=10, pady=(0, 4))

        # 拖动
        self._dx = self._dy = 0
        for wgt in [header, left, self.dot_c, self.lbl_status, self.lbl_time]:
            wgt.bind("<Button-1>", self._start_drag)
            wgt.bind("<B1-Motion>", self._on_drag)

        # 关闭窗口 = 停止录音并退出
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        log("=== CARD STARTED ===")

    # ---------- 拖动 ----------
    def _start_drag(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _on_drag(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def minimize(self):
        self.root.iconify()

    def on_close(self):
        log(f"on_close: state={self.state}")
        # 录音中直接关窗口 → 先停录音再退出
        if self.state == "recording":
            self._stop_flag()
        self.root.destroy()

    # ---------- 录音控制 ----------
    def _today_dir(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        d = RECORD_BASE / f"{today} 网课" / "录音"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _start_recording(self):
        self.out_dir = self._today_dir()
        # 清掉可能的旧 stop.flag，避免新录音立刻退出
        flag = self.out_dir / "stop.flag"
        if flag.exists():
            flag.unlink()
        script = SKILL_DIR / "start_record_detached.py"
        subprocess.Popen(
            [PYTHON, "-u", str(script), str(self.out_dir)],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True,
        )
        log(f"_start_recording -> {self.out_dir}")

    def _stop_flag(self):
        if self.out_dir:
            (self.out_dir / "stop.flag").write_text("")
            log(f"_stop_flag -> {self.out_dir / 'stop.flag'}")

    def on_start(self):
        log(f"on_start: state={self.state}")
        if self.state == "paused":
            # 继续录制（自动继承 seg 编号）
            self._start_recording()
            self.state = "recording"
            self._start_tick()
        else:
            self.elapsed = 0
            self._start_recording()
            self.state = "recording"
            self._start_tick()
        self._update_ui()

    def _start_tick(self):
        if self.timer_running:
            return
        self.timer_running = True
        self._tick()

    def _tick(self):
        if self.state == "recording":
            self.elapsed += 1
            m, s = divmod(self.elapsed, 60)
            self.lbl_time.config(text=f"{m:02d}:{s:02d}")
            self.root.after(1000, self._tick)
        else:
            self.timer_running = False

    def on_pause(self):
        log(f"on_pause: state={self.state}")
        if self.state == "recording":
            self._stop_flag()
            self.state = "paused"
            self.timer_running = False
            self._update_ui()

    def on_stop(self):
        log(f"on_stop: state={self.state}")
        self._stop_flag()
        m, s = divmod(self.elapsed, 60)
        self.state = "stopped"
        self.timer_running = False
        self.lbl_info.config(text=f"已录制 {m:02d}:{s:02d}")
        self._update_ui()

    # ---------- UI ----------
    def _update_ui(self):
        colors = {"idle": "#555", "recording": "#ef4444", "paused": "#f59e0b", "stopped": "#22c55e"}
        texts = {"idle": "就绪", "recording": "录制中", "paused": "已暂停", "stopped": "已结束"}
        self.dot_c.itemconfig(self.dot, fill=colors.get(self.state, "#555"))
        self.lbl_status.config(text=texts.get(self.state, "就绪"),
                               fg="#eee" if self.state in ("recording", "paused") else "#888")

        if self.state == "recording":
            self.btn_start.config(state="disabled", bg="#333", text="开始录制")
            self.btn_pause.config(state="normal", text="暂停")
            self.btn_stop.config(state="normal")
            self.lbl_info.config(text=f"录音中 · {self.out_dir}" if self.out_dir else "录音中")
        elif self.state == "paused":
            self.btn_start.config(state="normal", bg="#2563eb", text="继续")
            self.btn_pause.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.lbl_info.config(text="已暂停 · 点「开始录制」继续")
        elif self.state == "stopped":
            self.btn_start.config(state="normal", bg="#2563eb", text="重新录制")
            self.btn_pause.config(state="disabled")
            self.btn_stop.config(state="disabled")
            self.lbl_info.config(text=f"已结束 · {self.out_dir}" if self.out_dir else "已结束")
        else:
            self.btn_start.config(state="normal", bg="#2563eb", text="开始录制")
            self.btn_pause.config(state="disabled")
            self.btn_stop.config(state="disabled")
            self.lbl_info.config(text="")
        log(f"_update_ui -> state={self.state}, elapsed={self.elapsed}s")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    card = RecordCard()
    if "--auto-start" in sys.argv:
        card.root.after(600, card.on_start)
    card.run()
