import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from datetime import date, timedelta, datetime
import json
import os
import sys

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

BASE_FONT = "TkDefaultFont"
DIARY_FILE = os.path.join(APP_DIR, "calnlogs.json")

FONT_SIZES = {
    "small": 9,
    "medium": 11,
    "large": 14
}

def run_ui_with_error_handling(func):
    """Wrap UI callbacks to show messagebox on exception."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    return wrapper


class DiaryDataManager:
    def __init__(self, diary_file):
        self.diary_file = diary_file
        self.data = self.load_diary_data()

    def load_diary_data(self):
        if not os.path.isfile(self.diary_file):
            return {}
        try:
            with open(self.diary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # On failure, ignore and start with empty data
            return {}

    def save_diary_data(self):
        with open(self.diary_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get_note(self, date_str):
        return self.data.get(date_str, "")

    def set_note(self, date_str, content):
        if content:
            self.data[date_str] = content
        else:
            self.data.pop(date_str, None)

    def clear_note(self, date_str):
        self.data.pop(date_str, None)

class DateUtils:
    @staticmethod
    def format_date(d):
        return d.strftime("%Y-%m-%d")

    @staticmethod
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

class DiaryUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.date_utils = DateUtils()

        self.diary_file = DIARY_FILE
        self.data_manager = DiaryDataManager(self.diary_file)

        self.selected_date = date.today()
        self.selected_date_str = self.date_utils.format_date(self.selected_date)

        self.title("CalN")

        window_width, window_height = 800, 600
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(window_width, window_height)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.font_size = FONT_SIZES["large"]

        self.setup_ui()
        self.select_date(self.selected_date)

        # Save on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    @run_ui_with_error_handling
    def setup_ui(self):
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_bar.columnconfigure(0, weight=1)
        top_bar.columnconfigure(1, weight=0)

        self.current_date_label = ttk.Label(top_bar, text="", font=(BASE_FONT, 12, "bold"))
        self.current_date_label.grid(row=0, column=0, sticky="w")

        btn_frame = ttk.Frame(top_bar)
        btn_frame.grid(row=0, column=1, sticky="e")
        # Use grid for buttons for consistent layout
        buttons = [
            ("< Previous day", self.prev_day),
            ("Today", self.go_to_today),
            ("Next day >", self.next_day),
            ("Clear Note", self.clear_note),
            ("Go to Date", self.open_goto_date_dialog),
            ("Export Notes", self.export_notes_individually),
        ]
        for col, (text, cmd) in enumerate(buttons):
            ttk.Button(btn_frame, text=text, command=cmd).grid(row=0, column=col, padx=5)

        self.text_area = tk.Text(self, wrap="word", font=(BASE_FONT, self.font_size))
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.text_area.bind("<FocusOut>", lambda e: self.save_current_note())

    @run_ui_with_error_handling
    def select_date(self, dt):
        self.selected_date = dt
        self.selected_date_str = self.date_utils.format_date(dt)
        self.current_date_label.config(text=dt.strftime("%A, %B %d, %Y"))

        note = self.data_manager.get_note(self.selected_date_str)
        self.text_area.delete("1.0", "end")
        if note:
            self.text_area.insert("1.0", note)

    @run_ui_with_error_handling
    def prev_day(self):
        self._save_and_select(self.selected_date - timedelta(days=1))

    @run_ui_with_error_handling
    def next_day(self):
        self._save_and_select(self.selected_date + timedelta(days=1))

    @run_ui_with_error_handling
    def go_to_today(self):
        self._save_and_select(date.today())

    def _save_and_select(self, new_date):
        self.save_current_note()
        self.select_date(new_date)

    @run_ui_with_error_handling
    def save_current_note(self, event=None):
        if not getattr(self, 'selected_date_str', None):
            return
        content = self.text_area.get("1.0", "end").strip()
        # Save only if changed to minimize disk I/O
        if self.data_manager.get_note(self.selected_date_str) != content:
            self.data_manager.set_note(self.selected_date_str, content)
            self.data_manager.save_diary_data()

    @run_ui_with_error_handling
    def clear_note(self):
        if messagebox.askyesno("Confirm Clear", f"Clear notes for {self.selected_date_str}?"):
            self.data_manager.clear_note(self.selected_date_str)
            self.data_manager.save_diary_data()
            self.text_area.delete("1.0", "end")

    @run_ui_with_error_handling
    def open_goto_date_dialog(self):
        date_str = simpledialog.askstring("Go to Specific Day", "Enter a date (YYYY-MM-DD):",
                                          initialvalue=self.selected_date_str, parent=self)
        if not date_str:
            return
        dt = self.date_utils.parse_date(date_str.strip())
        if not dt:
            messagebox.showerror("Invalid Date", "Please enter a valid date in format YYYY-MM-DD.")
            return
        self._save_and_select(dt)

    @run_ui_with_error_handling
    def export_notes_individually(self):
        from tkinter import filedialog

        folder_path = filedialog.askdirectory(title="Select Folder to Export Notes")
        if not folder_path:
            return  # User cancelled

        try:
            for date_str, note in self.data_manager.data.items():
                safe_date = date_str.replace(":", "-")
                filename = f"{safe_date}.txt"
                file_path = os.path.join(folder_path, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(note.strip())

            messagebox.showinfo("Export Complete",
                                f"All notes have been exported as separate files to:\n{folder_path}")

        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export notes:\n{str(e)}")

    @run_ui_with_error_handling
    def on_close(self):
        self.save_current_note()
        self.destroy()

def main():
    DiaryUI().mainloop()

if __name__ == "__main__":
    main()
