import sys
import json
import csv
import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog

CIRCLE_THICKNESS = 4
SESSION_LOG_FILENAME = "pomozlogs.json"
POMODORO_DURATION = 25 * 60
BREAK_DURATION = 5 * 60
WINDOW_SIZE = (280, 320)
CIRCLE_SIZE = 180
BASE_FONT = ("Arial", 10)

GREY_COLOR = "#d0d0d0"
BLUE_COLOR = "#1E90FF"
BG_COLOR = "white"
FG_COLOR = "gray"

winsound = None
if sys.platform == "win32":
    import winsound

class SimplePomodoro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pomo")
        self.resizable(False, False)
        self._center_window(*WINDOW_SIZE)
        self.app_folder = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent.resolve()
        self.log_file = self.app_folder / SESSION_LOG_FILENAME
        self.session_log = self._load_session_log()
        self.is_running = False
        self.is_pomodoro = True
        self.time_left = POMODORO_DURATION
        self.timer_id = None
        self._build_ui()
        self._update_ui()
        self.bind("<space>", lambda _: self._toggle_timer())
        self.bind("r", lambda _: self._reset_timer())

    def _center_window(self, width, height):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = (sw - width) // 2, (sh - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        self.config(bg=BG_COLOR)
        self.session_label = tk.Label(self, font=BASE_FONT, bg=BG_COLOR, fg=FG_COLOR)
        self.session_label.pack(pady=(20, 5))
        self.canvas = tk.Canvas(self, width=CIRCLE_SIZE, height=CIRCLE_SIZE, bg=BG_COLOR, highlightthickness=0, cursor="hand2")
        self.canvas.pack(pady=5)
        self.canvas.bind("<Button-1>", lambda _: self._toggle_timer())
        self.timer_text = self.canvas.create_text(CIRCLE_SIZE // 2, CIRCLE_SIZE // 2, text="00:00", font=BASE_FONT, fill=BLUE_COLOR)
        self.status_label = tk.Label(self, font=BASE_FONT, bg=BG_COLOR, fg=FG_COLOR)
        self.status_label.pack(pady=(5, 15))
        menu_btn = tk.Menubutton(self, text="⋮", font=("Arial", 18, "bold"), relief="flat", cursor="hand2", width=2, bg=BG_COLOR)
        menu = tk.Menu(menu_btn, tearoff=0)
        menu.add_command(label="Reset Timer", command=self._reset_timer)
        menu.add_command(label="Export Log", command=self._export_log)
        menu.add_separator()
        menu.add_command(label="Quit", command=self.destroy)
        menu_btn.config(menu=menu)
        menu_btn.place(relx=1, rely=0, anchor="ne", x=-5, y=5)

    def _update_ui(self):
        self.session_label.config(text="Pomodoro session" if self.is_pomodoro else "Break session")
        margin = 10
        x0, y0, x1, y1 = margin, margin, CIRCLE_SIZE - margin, CIRCLE_SIZE - margin
        self.canvas.delete("progress_arc", "progress_arc_bg")
        self.canvas.create_oval(x0, y0, x1, y1, outline=GREY_COLOR, width=CIRCLE_THICKNESS, tags="progress_arc_bg")
        total = self._current_session_duration()
        elapsed = total - self.time_left
        extent = (elapsed / total) * 360 if total else 0
        arc_color = GREY_COLOR if extent < 0.3 else BLUE_COLOR
        self.canvas.create_arc(x0, y0, x1, y1, start=90, extent=-extent, style=tk.ARC, outline=arc_color, width=CIRCLE_THICKNESS, tags="progress_arc")
        mins, secs = divmod(self.time_left, 60)
        self.canvas.itemconfig(self.timer_text, text=f"{mins:02d}:{secs:02d}")
        if self.is_running:
            status = "Click circle to pause"
        elif self.time_left == total:
            status = "Click circle to start"
        else:
            status = "Click circle to resume"
        self.status_label.config(text=status)

    def _current_session_duration(self):
        return POMODORO_DURATION if self.is_pomodoro else BREAK_DURATION

    def _toggle_timer(self):
        self._pause_timer() if self.is_running else self._start_timer()

    def _start_timer(self):
        if not self.is_running:
            self.is_running = True
            self._count_down()
            self._update_ui()

    def _pause_timer(self):
        if self.is_running:
            self.is_running = False
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            self._update_ui()

    def _reset_timer(self):
        self._pause_timer()
        self.is_pomodoro = True
        self.time_left = POMODORO_DURATION
        self._update_ui()

    def _count_down(self):
        if self.is_running and self.time_left > 0:
            self.time_left -= 1
            self._update_ui()
            self.timer_id = self.after(1000, self._count_down)
        elif self.is_running and self.time_left == 0:
            self._session_finished()

    def _session_finished(self):
        self.is_running = False
        self.timer_id = None
        self._save_session()
        self._play_sound()
        self._switch_session()
        self._update_ui()

    def _switch_session(self):
        self.is_pomodoro = not self.is_pomodoro
        self.time_left = self._current_session_duration()

    def _save_session(self):
        today = datetime.date.today().isoformat()
        now = datetime.datetime.now().isoformat(timespec="seconds")
        duration = self._current_session_duration()
        session_type = "Pomodoro" if self.is_pomodoro else "Break"
        self.session_log.setdefault(today, []).append({
            "timestamp": now,
            "session_type": session_type,
            "duration_seconds": duration,
        })
        self._write_session_log()

    def _load_session_log(self):
        if self.log_file.exists():
            try:
                with self.log_file.open(encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _write_session_log(self):
        try:
            with self.log_file.open("w", encoding="utf-8") as f:
                json.dump(self.session_log, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save session log:\n{e}")

    def _export_log(self):
        if not self.session_log:
            messagebox.showinfo("Export Log", "No session data to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"Pomodoro_Sessions_{datetime.date.today().isoformat()}.csv",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Date", "Timestamp", "Session Type", "Duration (seconds)"])
                for date, sessions in sorted(self.session_log.items()):
                    for entry in sessions:
                        writer.writerow([date, entry["timestamp"], entry["session_type"], entry["duration_seconds"]])
            messagebox.showinfo("Export Log", f"Session log exported successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Log", f"Failed to export log:\n{e}")

    def _play_sound(self):
        if winsound:
            try:
                winsound.Beep(500, 1500)
            except RuntimeError:
                pass

if __name__ == "__main__":
    app = SimplePomodoro()
    app.mainloop()
