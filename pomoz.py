import tkinter as tk
from tkinter import messagebox, filedialog
import csv
import datetime
import json
import os
import sys

CIRCLE_THICKNESS = 4
SESSION_LOG="pomozlogs.json"

class SimplePomodoro(tk.Tk):
    POMODORO_DURATION = 25 * 60   # Change to 25*60 for production
    BREAK_DURATION = 5 * 60      # Change to 5*60 for production
    WINDOW_SIZE = (280, 320)
    CIRCLE_SIZE = 180

    def __init__(self):
        super().__init__()
        self.title("Pomo")
        self.resizable(False, False)
        self._center_window(*self.WINDOW_SIZE)
        self.app_folder = self._get_app_folder()
        self.log_file = os.path.join(self.app_folder, SESSION_LOG)

        self.is_running = False
        self.is_pomodoro = True
        self.time_left = self.POMODORO_DURATION
        self.timer_id = None
        self.session_log = self._load_session_log()

        self._build_ui()
        self._update_ui()
        self.bind("<space>", lambda e: self._toggle_timer())
        self.bind("r", lambda e: self._reset_timer())

    def _center_window(self, width, height):
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _get_app_folder(self):
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _build_ui(self):
        self.config(bg="white")
        font_main = ("Arial", 10)
        font_sm = ("Arial", 10)

        self.session_label = tk.Label(self, font=font_main, bg="white", fg="gray")
        self.session_label.pack(pady=(20, 5))

        self.canvas = tk.Canvas(self, width=self.CIRCLE_SIZE, height=self.CIRCLE_SIZE, bg="white",
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack(pady=5)
        self.canvas.bind("<Button-1>", lambda e: self._toggle_timer())

        self.timer_text = self.canvas.create_text(
            self.CIRCLE_SIZE // 2, self.CIRCLE_SIZE // 2,
            text="00:00", font=("Arial", 12, "bold"), fill="black"
        )

        self.status_label = tk.Label(self, font=font_sm, bg="white", fg="gray")
        self.status_label.pack(pady=(5, 15))

        menu_frame = tk.Frame(self, bg="white")
        menu_frame.place(relx=1, rely=0, anchor="ne", x=-5, y=5)

        self.menu_btn = tk.Menubutton(
            menu_frame, text="⋮", font=("Arial", 18, "bold"), relief="flat",
            cursor="hand2", width=2, bg="white"
        )
        self.menu_btn.pack()
        menu = tk.Menu(self.menu_btn, tearoff=0)
        menu.add_command(label="Reset Timer", command=self._reset_timer)
        menu.add_command(label="Export Log", command=self._export_log)
        menu.add_separator()
        menu.add_command(label="Quit", command=self.destroy)
        self.menu_btn.config(menu=menu)
        self.menu_btn.bind("<Enter>", lambda e: self.menu_btn.config(bg="#e0e0e0"))
        self.menu_btn.bind("<Leave>", lambda e: self.menu_btn.config(bg="white"))

    def _current_session_duration(self):
        return self.POMODORO_DURATION if self.is_pomodoro else self.BREAK_DURATION

    def _update_ui(self):
        self.session_label.config(
            text="Pomodoro session" if self.is_pomodoro else "Break session"
        )

        diameter = self.CIRCLE_SIZE
        margin = 10
        x0, y0 = margin, margin
        x1, y1 = diameter - margin, diameter - margin

        self.canvas.delete("progress_arc")
        self.canvas.delete("progress_arc_bg")

        self.canvas.create_oval(
            x0, y0, x1, y1,
            outline="#d0d0d0",
            width=CIRCLE_THICKNESS,
            tags="progress_arc_bg"
        )

        if self.is_running:
            self.canvas.itemconfigure(self.timer_text, state="hidden")
            total = self._current_session_duration()
            elapsed = total - self.time_left
            extent = (elapsed / total) * 360
            arc_color = "#1E90FF"

            self.canvas.create_arc(
                x0, y0, x1, y1,
                start=90,
                extent=-extent,
                style=tk.ARC,
                outline=arc_color,
                width=CIRCLE_THICKNESS,
                tags="progress_arc"
            )
            status_msg = "Click circle to pause"
        else:
            display_time = self.time_left if self.time_left != self._current_session_duration() else self._current_session_duration()
            mins, secs = divmod(display_time, 60)
            timer_str = f"{mins:02d}:{secs:02d}"

            self.canvas.itemconfig(
                self.timer_text,
                text=timer_str,
                fill="black",
                state="normal"
            )
            status_msg = "Click circle to start" if display_time == self._current_session_duration() else "Click circle to resume"

        self.status_label.config(text=status_msg)
        self.title("Pomo")

    def _toggle_timer(self):
        if self.is_running:
            self._pause_timer()
        else:
            self._start_timer()

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
        self.time_left = self.POMODORO_DURATION
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

        self.bell()
        self._update_ui()
        session_name = "Pomodoro" if self.is_pomodoro else "Break"
        messagebox.showinfo("Session Finished", f"{session_name} session finished!")
        self._switch_session()
        self._update_ui()

    def _switch_session(self):
        self.is_pomodoro = not self.is_pomodoro
        self.time_left = self.POMODORO_DURATION if self.is_pomodoro else self.BREAK_DURATION

    def _save_session(self):
        today_key = datetime.date.today().isoformat()
        now_iso = datetime.datetime.now().isoformat(timespec="seconds")
        duration = self.POMODORO_DURATION if self.is_pomodoro else self.BREAK_DURATION

        session_type = "Pomodoro" if self.is_pomodoro else "Break"
        self.session_log.setdefault(today_key, []).append({
            "timestamp": now_iso,
            "session_type": session_type,
            "duration_seconds": duration,
        })
        self._write_session_log()

    def _load_session_log(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _write_session_log(self):
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
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
                        writer.writerow([
                            date,
                            entry["timestamp"],
                            entry["session_type"],
                            entry["duration_seconds"],
                        ])
            messagebox.showinfo("Export Log", f"Session log exported successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Log", f"Failed to export log:\n{e}")

if __name__ == "__main__":
    app = SimplePomodoro()
    app.mainloop()
