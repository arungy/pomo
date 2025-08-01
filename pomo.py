import os
import sys
import tkinter as tk
from tkinter import messagebox, filedialog, Menu, ttk
import time
import tkinter.font as tkfont
import datetime
import pickle
import tempfile
import shutil
import concurrent.futures
import logging

try:
    import winsound
except ImportError:
    pass

# Constants for colors, fonts, durations
WINDOW_BG = "#f5f5f5"
START_RESET_BG = "#d3d3d3"
BUTTON_TEXT_COLOR = "#008000"
DEFAULT_POMODORO_DURATION = 25 * 60  # 25 minutes
DEFAULT_BREAK_DURATION = 5 * 60      # 5 minutes

def get_app_folder() -> str:
    """Return the path where the app is running."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class Tooltip:
    """Simple tooltip for Tkinter widgets.
    Shows a small tooltip label when hovering over a widget.
    """

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwin = None
        # Bind events to show/hide tooltip
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        # Avoid multiple tooltip windows or empty text
        if self.tipwin or not self.text:
            return
        try:
            x, y, _cx, cy = self.widget.bbox("insert") or (0, 0, 0, 0)
        except Exception:
            x, y, cy = 0, 0, 0
        # Calculate position near the widget
        x += self.widget.winfo_rootx() + 20
        y += cy + self.widget.winfo_rooty() + 25

        # Create tooltip window without window decorations
        self.tipwin = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        # Configure label inside tooltip
        label = tk.Label(
            tw,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Arial", 9),
        )
        label.pack(ipadx=4)

    def hide(self, event=None):
        if self.tipwin:
            self.tipwin.destroy()
            self.tipwin = None

def play_beep_real(duration_ms: int = 800, frequency: int = 450) -> None:
    """Play beep sound using winsound (Windows only), fallback does nothing."""
    try:
        winsound.Beep(frequency, duration_ms)
    except NameError:
        logging.info("Beep sound not supported on this platform.")

class SettingsManager:
    """Manage loading and saving of persistent application settings.

    Settings stored as a pickled dictionary with keys:
    - "date": str YYYY-MM-DD to reset daily count
    - "pomodoro": int count of pomodoros done today
    - "settings": nested dict for other config (mute, window position, etc.)
    """

    def __init__(self, filepath: str = None) -> None:
        if filepath is None:
            app_folder = get_app_folder()
            filepath = os.path.join(app_folder, "pomosettings.pkl")
        self.filepath = filepath
        self.data = self._load_settings()

    def _load_settings(self) -> dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "rb") as file:
                    data = pickle.load(file)
                    logging.debug("Settings loaded successfully.")
                    return data
            except Exception:
                logging.error("Failed to load settings.", exc_info=True)
        # Return default settings on failure or first run
        return {"date": "", "pomodoro": 0, "settings": {}}

    def save(self) -> None:
        # Write to temp file then atomically move to prevent corruption
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
                pickle.dump(self.data, tf, protocol=pickle.HIGHEST_PROTOCOL)
                tempname = tf.name
            shutil.move(tempname, self.filepath)
            logging.debug("Settings saved successfully.")
        except Exception:
            logging.error("Failed to save settings.", exc_info=True)

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        self.data[key] = value

    def get_nested(self, dict_key: str, inner_key: str, default=None):
        d = self.data.get(dict_key, {})
        return d.get(inner_key, default)

    def set_nested(self, dict_key: str, inner_key: str, value) -> None:
        if dict_key not in self.data or not isinstance(self.data[dict_key], dict):
            self.data[dict_key] = {}
        self.data[dict_key][inner_key] = value

class SessionLogManager:
    """Manage loading and saving Pomodoro session logs.

    Each log entry is a dict with keys:
    - timestamp: ISO format string
    - session_type: "pomodoro" or "break"
    - duration: duration in seconds
    """

    def __init__(self, filepath: str = None) -> None:
        if filepath is None:
            app_folder = get_app_folder()
            filepath = os.path.join(app_folder, "pomolog.pkl")
        self.filepath = filepath
        self.session_log = self._load_log()

    def _load_log(self) -> list:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "rb") as file:
                    log = pickle.load(file)
                    logging.debug("Session log loaded successfully.")
                    return log
            except Exception:
                logging.error("Failed to load session log.", exc_info=True)
        return []

    def save(self) -> None:
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
                pickle.dump(self.session_log, tf, protocol=pickle.HIGHEST_PROTOCOL)
                tempname = tf.name
            shutil.move(tempname, self.filepath)
            logging.debug("Session log saved successfully.")
        except Exception:
            logging.error("Failed to save session log.", exc_info=True)

    def append(self, entry: dict) -> None:
        self.session_log.append(entry)
        self.save()

    def get_all(self) -> list:
        return self.session_log

class SoundPlayer:
    """Asynchronously play beep sounds to avoid blocking the UI."""

    def __init__(self) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def play_beep(self, muted: bool = False) -> None:
        if muted:
            return
        self.executor.submit(play_beep_real, 800, 450)

class PomodoroTimer(tk.Tk):
    """Main Pomodoro Timer application window and logic."""

    def __init__(self) -> None:
        super().__init__()
        self._init_attributes()
        self._init_fonts()
        self._configure_window()
        self._create_widgets()
        self._load_settings()
        self._update_timer_label()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _init_attributes(self) -> None:
        self.settings = SettingsManager()
        # Use customized durations if available, else default.
        self.POMODORO_DURATION = int(self.settings.get_nested("settings", "pomodoro_minutes", 25)) * 60
        self.BREAK_DURATION = int(self.settings.get_nested("settings", "break_minutes", 5)) * 60

        self.session_log = SessionLogManager()
        self.sound_player = SoundPlayer()

        self.is_muted = False
        self.pomodoro_done = 0
        self.time_left = self.POMODORO_DURATION
        self.is_running = False
        self.current_session = "pomodoro"
        self.timer_job = None

    def _init_fonts(self) -> None:
        self.title_font = tkfont.Font(family="Arial", size=20, weight="bold")
        self.timer_font = tkfont.Font(family="Arial", size=28, weight="bold")
        self.button_font = tkfont.Font(family="Arial", size=12, weight="bold")
        self.info_font = tkfont.Font(family="Arial", size=10)

    def _configure_window(self) -> None:
        # Configure window position and size from saved settings
        self.option_add("*Font", "Arial 11")
        self.title("Pomo")
        self.configure(bg=WINDOW_BG)
        self.resizable(False, False)
        pos = self.settings.get_nested("settings", "window_position", None)
        width, height = 300, 350
        if pos and isinstance(pos, (list, tuple)) and len(pos) == 2:
            x, y = pos
            self.geometry(f"{width}x{height}+{x}+{y}")
        else:
            self.geometry(f"{width}x{height}")

    def _load_settings(self) -> None:
        # Reset daily pomodoro count if date changed
        today = self._get_today_key()
        if self.settings.get("date") != today:
            self.settings.set("date", today)
            self.settings.set("pomodoro", 0)
            self.settings.save()
        self.is_muted = self.settings.get_nested("settings", "muted", False)
        self.pomodoro_done = self.settings.get("pomodoro", 0)
        # Reload durations in case user edited the settings file directly:
        self.POMODORO_DURATION = int(self.settings.get_nested("settings", "pomodoro_minutes", 25)) * 60
        self.BREAK_DURATION = int(self.settings.get_nested("settings", "break_minutes", 5)) * 60

    def _create_widgets(self) -> None:
        self.main_frame = tk.Frame(self, bg=WINDOW_BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self._create_top_controls()
        self._create_timer_display()
        self._create_control_buttons()
        self._create_history_view()

    def _create_top_controls(self) -> None:
        top_frame = tk.Frame(self.main_frame, bg=WINDOW_BG)
        top_frame.pack(fill=tk.X, pady=(8, 3), padx=5)

        spacer = tk.Label(top_frame, bg=WINDOW_BG)
        spacer.pack(side=tk.LEFT, expand=True)

        self.reset_icon_btn = tk.Button(
            top_frame,
            text="⟲",
            font=("Arial", 14),
            relief="flat",
            bg="white",
            activebackground="#ddeeff",
            cursor="hand2",
            command=self._reset_timer,
        )

        self.menu_btn = tk.Menubutton(
            top_frame,
            text="⋮",
            font=("Arial", 18, "bold"),
            relief="flat",
            padx=6,
            pady=4,
            bg="white",
            activebackground="#ddeeff",
            bd=1,
            cursor="hand2",
            highlightthickness=0,
        )
        self.menu_btn.pack(side=tk.RIGHT, padx=(3, 5))
        self.reset_icon_btn.pack(side=tk.RIGHT, padx=(3, 5))
        Tooltip(self.reset_icon_btn, "Reset timer")
        Tooltip(self.menu_btn, "More options")  # Tooltip added here

        self.popup_menu = Menu(self.menu_btn, tearoff=0, font=self.info_font)
        self.popup_menu.add_command(label="", command=self._toggle_mute)
        self._update_mute_menu_label()
        self.popup_menu.add_command(label="Session history", command=self._show_history_view)
        self.popup_menu.add_command(label="Change duration", command=self._open_duration_dialog)
        self.popup_menu.add_command(label="Export CSV", command=self._export_csv)
        self.menu_btn.config(menu=self.popup_menu)

    def _update_mute_menu_label(self) -> None:
        label = "Mute sound" if not self.is_muted else "Unmute sound"
        if hasattr(self, "popup_menu"):
            if self.popup_menu.index("end") is not None:
                self.popup_menu.entryconfig(0, label=label)
            else:
                self.popup_menu.add_command(label=label, command=self._toggle_mute)

    def _create_timer_display(self) -> None:
        self.session_label = tk.Label(
            self.main_frame,
            bg=WINDOW_BG,
            fg="#333",
            font=self.button_font,
            wraplength=360,
            justify=tk.CENTER,
            text="Choose pomodoro",
        )
        self.session_label.pack(pady=(10, 9))

        self.timer_label = tk.Label(
            self.main_frame,
            bg=WINDOW_BG,
            fg="#222",
            font=self.timer_font,
            padx=20,
            pady=15,
            width=5,
            anchor="center",
            justify=tk.CENTER,
            text="00:00",
        )
        self.timer_label.pack(pady=(0, 14))

    def _create_control_buttons(self) -> None:
        center_container = tk.Frame(self.main_frame, bg=WINDOW_BG)
        center_container.pack(fill=tk.BOTH, expand=True)

        ctrl_frame = tk.Frame(center_container, bg=WINDOW_BG)
        ctrl_frame.pack()

        style = ttk.Style()
        style.configure(
            "Pomo.TButton",
            font=("Arial", 10, "bold"),
            padding=(6, 4),
            foreground=BUTTON_TEXT_COLOR,
            background=START_RESET_BG,
        )

        self.pause_button = ttk.Button(
            ctrl_frame,
            text="Start",
            command=self._pause_resume,
            style="Pomo.TButton",
            cursor="hand2",
        )
        self.pause_button.grid(row=0, column=0, pady=3, sticky="ns")

    def _create_history_view(self) -> None:
        self.history_frame = tk.Frame(self, bg=WINDOW_BG)
        self.history_frame.grid_rowconfigure(1, weight=1)
        self.history_frame.grid_columnconfigure(0, weight=1)

        back_label_frame = tk.Frame(self.history_frame, bg=WINDOW_BG)
        back_label_frame.grid(row=0, column=0, sticky="ew")
        back_label_frame.grid_columnconfigure(0, weight=1)

        self.back_label = tk.Label(
            back_label_frame,
            text="back",
            font=self.info_font,
            fg="black",
            bg=WINDOW_BG,
            cursor="hand2",
        )
        self.back_label.grid(row=0, column=1, sticky="e", padx=10, pady=10)
        self.back_label.bind("<Button-1>", lambda e: self._show_timer_view())

        self.history_text = tk.Text(
            self.history_frame,
            bg=WINDOW_BG,
            fg="black",
            font=self.info_font,
            wrap="word",
            state="disabled",
            padx=10,
            pady=10,
            relief="flat",
            borderwidth=0,
        )
        self.history_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _pause_resume(self) -> None:
        # Update session label according to current session
        if self.current_session == "pomodoro":
            self.session_label.config(text="Pomodoro session", fg="#333")
        else:
            self.session_label.config(text="Break session", fg="#333")
        if self.is_running:
            self._pause_timer()
        else:
            self._start_timer()

    def _start_timer(self) -> None:
        self.is_running = True
        self.pause_button.config(text="Pause")
        self.timer_label.config(fg="#4a90e2")
        self._schedule_tick()

    def _pause_timer(self) -> None:
        self.is_running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self.pause_button.config(text="Start")
        self.timer_label.config(fg="#333")

    def _schedule_tick(self) -> None:
        if self.is_running:
            if self.time_left > 0:
                self.timer_job = self.after(1000, self._timer_tick)
            else:
                self._end_session()

    def _timer_tick(self) -> None:
        if self.is_running and self.time_left > 0:
            self.time_left -= 1
            self._update_timer_label()
            self._schedule_tick()
        elif self.is_running and self.time_left == 0:
            self._end_session()

    def _update_timer_label(self) -> None:
        mins, secs = divmod(self.time_left, 60)
        self.timer_label.config(text=f"{mins}:{secs:02d}")

    def _reset_timer(self, event=None) -> None:
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self.POMODORO_DURATION = int(self.settings.get_nested("settings", "pomodoro_minutes", 25)) * 60
        self.BREAK_DURATION = int(self.settings.get_nested("settings", "break_minutes", 5)) * 60
        self.time_left = self.POMODORO_DURATION
        self.is_running = False
        self.current_session = "pomodoro"
        self._update_timer_label()
        self.session_label.config(text="Choose pomodoro", fg="#333")
        self.timer_label.config(fg="#333")
        self.pause_button.config(text="Start")

    def _end_session(self) -> None:
        self.is_running = False
        self.pause_button.config(text="Start")
        # Play beep sound unless muted
        self.sound_player.play_beep(muted=self.is_muted)

        now_iso = datetime.datetime.now().isoformat(timespec="seconds")
        session_data = {
            "timestamp": now_iso,
            "session_type": self.current_session,
            "duration": self.POMODORO_DURATION if self.current_session == "pomodoro" else self.BREAK_DURATION,
        }
        self.session_log.append(session_data)

        if self.current_session == "pomodoro":
            self.pomodoro_done += 1
            self.settings.set("pomodoro", self.pomodoro_done)
            self.settings.save()
            # Switch to break session
            self.current_session = "break"
            self.BREAK_DURATION = int(self.settings.get_nested("settings", "break_minutes", 5)) * 60
            self.time_left = self.BREAK_DURATION
            self.session_label.config(text="Break session", fg="#333", font=self.button_font)
            self.timer_label.config(fg="#333")
            self._update_timer_label()
        else:
            # Switch back to pomodoro session
            self.current_session = "pomodoro"
            self.POMODORO_DURATION = int(self.settings.get_nested("settings", "pomodoro_minutes", 25)) * 60
            self.time_left = self.POMODORO_DURATION
            self.session_label.config(text="Choose pomodoro", fg="#333", font=self.button_font)
            self.timer_label.config(fg="#333")
            self._update_timer_label()

    def _toggle_mute(self) -> None:
        # Toggle mute state and update menu label
        self.is_muted = not self.is_muted
        self.settings.set_nested("settings", "muted", self.is_muted)
        self.settings.save()
        self._update_mute_menu_label()

    def _export_csv(self) -> None:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"Pomodoro_Sessions_{self._get_today_key()}.csv",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write("Timestamp,Session Type,Duration (seconds)\n")
                for entry in self.session_log.get_all():
                    file.write(f"{entry['timestamp']},{entry['session_type']},{entry['duration']}\n")
        except Exception as exc:
            messagebox.showerror("Export CSV", f"Failed to export CSV:\n{exc}")

    def _show_history_view(self) -> None:
        self.main_frame.pack_forget()
        self.history_frame.pack(fill=tk.BOTH, expand=True)
        lines = [f"Pomodoro sessions done today: {self.pomodoro_done}"]
        text_content = "\n".join(lines)
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        self.history_text.insert("1.0", text_content)
        self.history_text.config(state=tk.DISABLED)

    def _show_timer_view(self) -> None:
        self.history_frame.pack_forget()
        self.main_frame.pack(fill=tk.BOTH, expand=True)

    def _on_closing(self) -> None:
        try:
            geom = self.geometry()
            pos = geom.split("+")[1:]
            if len(pos) == 2:
                x, y = int(pos[0]), int(pos[1])
                self.settings.set_nested("settings", "window_position", (x, y))
                self.settings.save()
        except Exception as exc:
            logging.warning("Saving window position failed: %s", exc)
        self.destroy()

    @staticmethod
    def _get_today_key() -> str:
        return time.strftime("%Y-%m-%d")

    # == SETTINGS DIALOG ==
    def _open_duration_dialog(self):
        return
        
        top = tk.Toplevel(self)
        top.title("Change duration")
        top.resizable(False, False)
        top.configure(bg=WINDOW_BG)

        tk.Label(top, text="Pomodoro (minutes):", bg=WINDOW_BG).grid(row=0, column=0, padx=10, pady=6, sticky="e")
        tk.Label(top, text="Break (minutes):", bg=WINDOW_BG).grid(row=1, column=0, padx=10, pady=6, sticky="e")

        pomo_var = tk.StringVar(value=str(self.settings.get_nested("settings", "pomodoro_minutes", 25)))
        break_var = tk.StringVar(value=str(self.settings.get_nested("settings", "break_minutes", 5)))

        pomo_entry = tk.Entry(top, textvariable=pomo_var, width=5)
        break_entry = tk.Entry(top, textvariable=break_var, width=5)
        pomo_entry.grid(row=0, column=1, padx=10, pady=6)
        break_entry.grid(row=1, column=1, padx=10, pady=6)

        def save_and_close():
            try:
                pomo = max(1, int(pomo_var.get()))
                brk = max(1, int(break_var.get()))
                self.settings.set_nested("settings", "pomodoro_minutes", pomo)
                self.settings.set_nested("settings", "break_minutes", brk)
                self.settings.save()
                self.POMODORO_DURATION = pomo * 60
                self.BREAK_DURATION = brk * 60
                # Adjust time_left ONLY if timer is not running
                if not self.is_running:
                    if self.current_session == "pomodoro":
                        self.time_left = self.POMODORO_DURATION
                    else:
                        self.time_left = self.BREAK_DURATION
                    self._update_timer_label()
                messagebox.showinfo("Change duration", "Durations saved!")
                top.destroy()
            except Exception:
                messagebox.showerror("Error", "Please enter valid numbers ≥ 1.")

        tk.Button(top, text="Save", command=save_and_close).grid(row=2, column=0, columnspan=2, pady=12)
        top.grab_set()

def main() -> None:
    """Run the Pomodoro timer app."""
    app = PomodoroTimer()
    # Uncomment to test with shorter durations:
    # app.POMODORO_DURATION = 60
    # app.BREAK_DURATION = 60
    app.time_left = app.POMODORO_DURATION
    app.mainloop()

if __name__ == "__main__":
    main()
