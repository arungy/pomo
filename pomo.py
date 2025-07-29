import os
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
import time
import threading
import tkinter.font as tkfont
import datetime
import pickle
import tempfile
import shutil
import concurrent.futures
import traceback

try:
    import winsound
    def play_beep_real(duration_ms=800, frequency=450):
        winsound.Beep(frequency, duration_ms)
except ImportError:
    def play_beep_real(duration_ms=800, frequency=450):
        pass  # No sound on non-Windows platforms or missing winsound

def get_app_folder():
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as a script
        return os.path.dirname(os.path.abspath(__file__))

APP_FOLDER = get_app_folder()
DATA_FILE_SETTINGS = os.path.join(APP_FOLDER, "pomosettings.pkl")
DATA_FILE_LOG = os.path.join(APP_FOLDER, "pomolog.pkl")

# UI Colors
RESET_BG = "#f4a261"
RESET_ACTIVE_BG = "#e9a46c"
PAUSE_BG = "#999999"
PAUSE_ACTIVE_BG = "#777777"
RESUME_BG = "#43a047"
RESUME_ACTIVE_BG = "#388e3c"
POMODORO_BTN_BG = "#4a90e2"
POMODORO_BTN_ACTIVE_BG = "#357ABD"
EXPORT_BTN_BG = "#4a90e2"       # Blue color for Export CSV button
EXPORT_BTN_ACTIVE_BG = "#357ABD"

class SettingsManager:
    """Handle loading and saving settings and counters."""

    def __init__(self, filepath=DATA_FILE_SETTINGS):
        self.filepath = filepath
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "rb") as f:
                    return pickle.load(f)
            except Exception:
                traceback.print_exc()
        # Default structure
        return {
            "date": "",
            "pomodoro": 0,
            "break": 0,
            "settings": {},  # e.g. {"muted": False, "window_position": (x, y), ...}
        }

    def save(self):
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
                pickle.dump(self.data, tf, protocol=pickle.HIGHEST_PROTOCOL)
                tempname = tf.name
            shutil.move(tempname, self.filepath)
        except Exception as e:
            print(f"Failed to save settings: {e}")
            traceback.print_exc()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def get_nested(self, dict_key, inner_key, default=None):
        d = self.data.get(dict_key, {})
        return d.get(inner_key, default)

    def set_nested(self, dict_key, inner_key, value):
        if dict_key not in self.data or not isinstance(self.data[dict_key], dict):
            self.data[dict_key] = {}
        self.data[dict_key][inner_key] = value

class SessionLogManager:
    """Handle loading and saving session logs."""

    def __init__(self, filepath=DATA_FILE_LOG):
        self.filepath = filepath
        self.session_log = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "rb") as f:
                    return pickle.load(f)
            except Exception:
                traceback.print_exc()
        return []

    def save(self):
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
                pickle.dump(self.session_log, tf, protocol=pickle.HIGHEST_PROTOCOL)
                tempname = tf.name
            shutil.move(tempname, self.filepath)
        except Exception as e:
            print(f"Failed to save session log: {e}")
            traceback.print_exc()

    def append(self, entry):
        self.session_log.append(entry)
        self.save()

    def get_all(self):
        return self.session_log

class SoundPlayer:
    """Asynchronous beep sound player."""

    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def play_beep(self, session_type=None, muted=False):
        if muted:
            return
        duration = 800   # ms
        frequency = 450  # Hz
        self.executor.submit(play_beep_real, duration, frequency)

class PomodoroTimer(tk.Tk):
    POMODORO_DURATION = 25 * 60
    BREAK_DURATION = 5 * 60

    def __init__(self):
        super().__init__()
        self.title("Pomo")
        self.configure(bg="#f5f5f5")

        # Managers
        self.settings = SettingsManager()
        self.session_log = SessionLogManager()
        self.sound_player = SoundPlayer()

        width, height = 400, 440
        pos = self.settings.get_nested("settings", "window_position")
        if pos and isinstance(pos, (list, tuple)) and len(pos) == 2:
            x, y = pos
            self.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.geometry(f"{width}x{height}")

        self.resizable(False, False)

        # Daily counters logic - reset if needed
        today_key = self.get_today_key()
        if self.settings.get("date") != today_key:
            self.settings.set("date", today_key)
            self.settings.set("pomodoro", 0)
            self.settings.set("break", 0)
            self.settings.save()

        self.pomodoro_done = self.settings.get("pomodoro", 0)
        self.break_done = self.settings.get("break", 0)

        # User settings dict (e.g. muted state)
        self.user_settings = self.settings.get("settings", {})
        self.is_muted = self.user_settings.get("muted", False)

        self.time_left = 0
        self.is_running = False
        self.current_session = None
        self.timer_job = None

        self._init_fonts()
        self._create_widgets()
        self._update_mute_ui()
        self.update_counts_display()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        try:
            geom = self.geometry()
            pos = geom.split('+')[1:]
            if len(pos) == 2:
                x, y = int(pos[0]), int(pos[1])
                self.user_settings["window_position"] = (x, y)
                self.settings.set_nested("settings", "window_position", (x, y))
                self.settings.save()
        except Exception:
            pass
        self.destroy()

    def _init_fonts(self):
        self.title_font = tkfont.Font(family="Arial", size=20, weight="bold")
        self.timer_font = tkfont.Font(family="Arial", size=42, weight="bold")
        self.button_font = tkfont.Font(family="Arial", size=11, weight="bold")
        self.info_font = tkfont.Font(family="Arial", size=10)
        self.mute_label_font = tkfont.Font(family="Arial", size=10, weight="bold")

    def _create_widgets(self):
        top_frame = tk.Frame(self, bg="#f5f5f5")
        top_frame.pack(fill='x', pady=(8, 3), padx=10)

        spacer = tk.Label(top_frame, bg="#f5f5f5", text="")
        spacer.pack(side='left', expand=True)

        self.mute_btn = tk.Button(
            top_frame, font=("Arial", 16), command=self.toggle_mute, relief='flat',
            padx=8, pady=4, bg="white", activebackground="#ddeeff", bd=1,
            highlightthickness=0, cursor="hand2"
        )
        self.mute_btn.pack(side='right', padx=(0, 5))
        self.mute_btn.bind("<Enter>", lambda e: self.show_tooltip(e, "Toggle sound"))
        self.mute_btn.bind("<Leave>", self.hide_tooltip)

        self.mute_status_label = tk.Label(
            top_frame, text="", bg="#f5f5f5", fg="#555", font=self.mute_label_font
        )
        self.mute_status_label.pack(side='right', padx=(0, 10))

        self.session_label = tk.Label(
            self, text="Choose an option", bg="#f5f5f5", fg="#333",
            font=self.title_font, wraplength=360, justify=tk.CENTER
        )
        self.session_label.pack(pady=(0, 9))

        self.timer_label = tk.Label(
            self, text="00:00", bg="#f5f5f5", fg="#222",
            font=self.timer_font, padx=10, pady=5,
            width=5,
            anchor="center",
            justify=tk.CENTER
        )
        self.timer_label.pack(pady=(0, 14))

        btn_frame = tk.Frame(self, bg="#f5f5f5")
        btn_frame.pack(pady=(0, 9), fill='x', padx=10)

        for i in range(5):
            btn_frame.columnconfigure(i, weight=1 if i in (0, 4) else 0)

        btn_width = 14
        btn_padx = 6
        btn_pady = 6

        self.pomodoro_btn = tk.Button(
            btn_frame, text="Pomodoro (25 min)", command=self.start_pomodoro,
            font=self.button_font, bd=0,
            bg=POMODORO_BTN_BG, fg="white",
            activebackground=POMODORO_BTN_ACTIVE_BG, activeforeground="white",
            cursor="hand2", relief="raised",
            width=btn_width, padx=btn_padx, pady=btn_pady
        )
        self.pomodoro_btn.grid(row=0, column=1, sticky="nsew", pady=3)

        tk.Frame(btn_frame, width=10, bg="#f5f5f5").grid(row=0, column=2)

        self.break_btn = tk.Button(
            btn_frame, text="Break (5 min)", command=self.start_break,
            font=self.button_font, bd=0,
            bg=POMODORO_BTN_BG, fg="white",
            activebackground=POMODORO_BTN_ACTIVE_BG, activeforeground="white",
            cursor="hand2", relief="raised",
            width=btn_width, padx=btn_padx, pady=btn_pady
        )
        self.break_btn.grid(row=0, column=3, sticky="nsew", pady=3)

        ctrl_frame = tk.Frame(self, bg="#f5f5f5")
        ctrl_frame.pack(pady=(0, 9), fill='x', padx=10)

        for i in range(5):
            ctrl_frame.columnconfigure(i, weight=1 if i in (0, 4) else 0)

        ctrl_btn_width = 11
        ctrl_btn_padx = 6
        ctrl_btn_pady = 6

        self.pause_btn = tk.Button(
            ctrl_frame, text="Pause",
            command=self.pause_resume,
            state=tk.DISABLED,
            font=self.button_font, bd=0,
            bg=PAUSE_BG, fg="white",
            activebackground=PAUSE_ACTIVE_BG, activeforeground="white",
            cursor="hand2", relief="raised",
            width=ctrl_btn_width, padx=ctrl_btn_padx, pady=ctrl_btn_pady
        )
        self.pause_btn.grid(row=0, column=1, sticky="nsew", pady=3)

        tk.Frame(ctrl_frame, width=10, bg="#f5f5f5").grid(row=0, column=2)

        self.reset_btn = tk.Button(
            ctrl_frame, text="Reset", command=self.reset_timer, state=tk.DISABLED,
            font=self.button_font, bd=0,
            bg=PAUSE_BG, fg="white",
            activebackground=PAUSE_ACTIVE_BG, activeforeground="white",
            cursor="hand2", relief="raised",
            width=ctrl_btn_width, padx=ctrl_btn_padx, pady=ctrl_btn_pady
        )
        self.reset_btn.grid(row=0, column=3, sticky="nsew", pady=3)

        self.summary_label = tk.Label(
            self, font=self.info_font, bg="#f5f5f5", fg="#444"
        )
        self.summary_label.pack(pady=(0, 9))

        self.export_btn = tk.Button(
            self, text="Export CSV",
            command=self.export_csv,
            font=self.button_font, width=20, bd=0,
            bg=EXPORT_BTN_BG, fg="white",
            activebackground=EXPORT_BTN_ACTIVE_BG, activeforeground="white",
            cursor="hand2"
        )
        self.export_btn.pack(pady=6)

        self.tooltip = tk.Label(
            self, bg="#ffffcc", fg="#333", font=self.info_font, bd=1, relief='solid'
        )
        self.tooltip.place_forget()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        self.user_settings["muted"] = self.is_muted
        self.settings.set_nested("settings", "muted", self.is_muted)
        self.settings.save()
        self._update_mute_ui()

    def _update_mute_ui(self):
        self.mute_btn.config(text="🔇" if self.is_muted else "🔈")
        self.mute_status_label.config(text="Muted" if self.is_muted else "Unmuted")

    def play_beep(self, session_type=None):
        self.sound_player.play_beep(session_type, muted=self.is_muted)

    def update_counts_display(self):
        self.summary_label.config(
            text=f"Pomodoro sessions done today: {self.pomodoro_done}\nBreak sessions done today: {self.break_done}"
        )

    def update_timer_label(self):
        mins, secs = divmod(self.time_left, 60)
        self.timer_label.config(text=f"{mins:>2d}:{secs:02d}")

    def _start_session(self, duration, session_type):
        self.cancel_timer()
        self.time_left = duration
        self.current_session = session_type
        self.is_running = True

        self.session_label.config(text=f"{session_type.capitalize()} session", fg="#4a90e2")
        self.update_timer_label()

        self.pause_btn.config(state=tk.NORMAL, text="Pause",
                              bg=PAUSE_BG, activebackground=PAUSE_ACTIVE_BG,
                              fg="white", activeforeground="white")
        self.reset_btn.config(state=tk.NORMAL,
                              bg=RESET_BG, activebackground=RESET_ACTIVE_BG,
                              fg="white", activeforeground="white")

        self.pomodoro_btn.config(state=tk.DISABLED)
        self.break_btn.config(state=tk.DISABLED)

        self.play_beep(session_type)
        self._schedule_tick()

    def start_pomodoro(self):
        self._start_session(self.POMODORO_DURATION, "pomodoro")

    def start_break(self):
        self._start_session(self.BREAK_DURATION, "break")

    def _schedule_tick(self):
        if self.is_running and self.time_left > 0:
            self.timer_job = self.after(1000, self._timer_tick)
        elif self.is_running and self.time_left == 0:
            self._end_session()

    def _timer_tick(self):
        if self.is_running:
            self.time_left -= 1
            self.update_timer_label()
            if self.time_left > 0:
                self._schedule_tick()
            else:
                self._end_session()

    def pause_resume(self):
        if self.is_running:
            self.is_running = False
            self.pause_btn.config(text="Resume", bg=RESUME_BG, activebackground=RESUME_ACTIVE_BG,
                                  fg="white", activeforeground="white")
            self.reset_btn.config(state=tk.NORMAL, bg=RESET_BG, activebackground=RESET_ACTIVE_BG,
                                  fg="white", activeforeground="white")
            if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
        else:
            self.is_running = True
            self.pause_btn.config(text="Pause", bg=PAUSE_BG, activebackground=PAUSE_ACTIVE_BG,
                                  fg="white", activeforeground="white")
            self.reset_btn.config(state=tk.NORMAL, bg=RESET_BG, activebackground=RESET_ACTIVE_BG,
                                  fg="white", activeforeground="white")
            self._schedule_tick()

    def reset_timer(self):
        self.cancel_timer()
        self.time_left = 0
        self.current_session = None
        self.is_running = False

        self.timer_label.config(text="00:00")
        self.session_label.config(text="Choose an option", fg="#333", wraplength=360, justify=tk.CENTER)
        self.pomodoro_btn.config(state=tk.NORMAL)
        self.break_btn.config(state=tk.NORMAL)

        self.pause_btn.config(state=tk.DISABLED, text="Pause", bg=PAUSE_BG, activebackground=PAUSE_ACTIVE_BG,
                              fg="white", activeforeground="white")
        self.reset_btn.config(state=tk.DISABLED, bg=PAUSE_BG, activebackground=PAUSE_ACTIVE_BG,
                              fg="white", activeforeground="white")

    def cancel_timer(self):
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None

    def _end_session(self):
        self.is_running = False

        self.pause_btn.config(state=tk.DISABLED, bg=PAUSE_BG, activebackground=PAUSE_ACTIVE_BG,
                              fg="white", activeforeground="white")
        self.reset_btn.config(state=tk.DISABLED, bg=PAUSE_BG, activebackground=PAUSE_ACTIVE_BG,
                              fg="white", activeforeground="white")

        self.pomodoro_btn.config(state=tk.NORMAL)
        self.break_btn.config(state=tk.NORMAL)
        self.pause_btn.config(text="Pause")

        self.play_beep(self.current_session)

        if self.current_session == "pomodoro":
            self.pomodoro_done += 1
            self.settings.set("pomodoro", self.pomodoro_done)
        elif self.current_session == "break":
            self.break_done += 1
            self.settings.set("break", self.break_done)
        self.settings.save()

        entry = {
            "timestamp": datetime.datetime.now().isoformat(timespec='seconds'),
            "session_type": self.current_session,
            "duration": self.POMODORO_DURATION if self.current_session == "pomodoro" else self.BREAK_DURATION
        }
        self.session_log.append(entry)

        self.update_counts_display()

        self.session_label.config(text="Choose an option", fg="#333", wraplength=360, justify=tk.CENTER)
        self.timer_label.config(text="00:00")
        self.current_session = None

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"Pomodoro_Sessions_{self.get_today_key()}.csv"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding='utf-8') as f:
                f.write("Timestamp,Session Type,Duration (seconds)\n")
                for entry in self.session_log.get_all():
                    f.write(f"{entry['timestamp']},{entry['session_type']},{entry['duration']}\n")
            messagebox.showinfo("Export CSV", f"CSV exported successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Failed to export CSV:\n{e}")

    def show_tooltip(self, event, text):
        self.tooltip.config(text=text)
        self.tooltip.place(x=event.widget.winfo_rootx() - self.winfo_rootx(),
                           y=event.widget.winfo_rooty() - self.winfo_rooty() + event.widget.winfo_height())

    def hide_tooltip(self, event):
        self.tooltip.place_forget()

    @staticmethod
    def get_today_key():
        return time.strftime("%Y-%m-%d")

if __name__ == "__main__":
    PomodoroTimer().mainloop()

