import tkinter as tk
from tkinter import messagebox, simpledialog, Menu, filedialog
from datetime import date, timedelta, datetime
import json, os, sys

# =========================================================
# CONFIGURATION
# =========================================================
APP_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
DIARY_FILE = os.path.join(APP_DIR, "calnlogs.json")

BASE_FONT = "SF Mono"
FONT_SIZES = {"small": 9, "medium": 11, "large": 13}

# =========================================================
# UTILITIES
# =========================================================
def run_ui_with_error_handling(func):
    """Decorator to catch UI errors and show pop-up messages."""
    def wrapper(*a, **kw):
        try:
            return func(*a, **kw)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    return wrapper

class DateUtils:
    """Utility functions for date parsing and formatting."""
    @staticmethod
    def format(d):
        return d.strftime("%Y-%m-%d")

    @staticmethod
    def parse(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None

# =========================================================
# DATA MANAGER
# =========================================================
class DiaryDataManager:
    """Handles loading, saving, and managing diary notes."""
    def __init__(self, path):
        self.path = path
        self.data = self.load()

    def load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get(self, date_str):
        return self.data.get(date_str, "")

    def set(self, date_str, content):
        if content:
            self.data[date_str] = content
        else:
            self.data.pop(date_str, None)

    def clear(self, date_str):
        self.data.pop(date_str, None)

# =========================================================
# USER INTERFACE
# =========================================================
class DiaryUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CalN")

        # Core Components
        self.data_mgr = DiaryDataManager(DIARY_FILE)
        self.date_utils = DateUtils()
        self.font_size = FONT_SIZES["medium"]
        self.selected_date = date.today()
        self.selected_date_str = self.date_utils.format(self.selected_date)

        # Launch Maximized with Title Bar
        self._maximize_window()

        # Configure Layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # UI Setup
        
        self._setup_ui()
        self._create_context_menu()
        self._select_date(self.selected_date)

        # Exit Handling
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _maximize_window(self):
        """Start app maximized but keep title bar."""
        try:
            self.state("zoomed")  # Works on Windows
        except:
            self.attributes('-zoomed', True)  # Linux/macOS fallback

    # -----------------------------------------------------
    # UI CREATION
    # -----------------------------------------------------
    @run_ui_with_error_handling
    def _setup_ui(self):
        # Top Bar with Current Date
        top_bar = tk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_bar.columnconfigure(0, weight=1)

        self.current_date_label = tk.Label(top_bar, font=(BASE_FONT, 12))
        self.current_date_label.grid(row=0, column=0, sticky="w")

        # Text Area for Notes
        self.text_area = tk.Text(self, wrap="word",
                                 font=(BASE_FONT, self.font_size))
        self.text_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.text_area.bind("<FocusOut>", lambda e: self.save_note())
        self.text_area.bind("<Button-3>", self._show_context_menu)

    def _create_context_menu(self):
        """Right-click menu for navigation and actions."""
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Previous Day", command=self.prev_day)
        self.context_menu.add_command(label="Today", command=self.go_to_today)
        self.context_menu.add_command(label="Next Day", command=self.next_day)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Clear Note", command=self.clear_note)
        self.context_menu.add_command(label="Go to Date", command=self.goto_date)
        self.context_menu.add_command(label="Export Notes", command=self.export_notes)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Quit", command=self.on_close)

    def _show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # -----------------------------------------------------
    # DATE NAVIGATION
    # -----------------------------------------------------
    @run_ui_with_error_handling
    def _select_date(self, dt):
        self.selected_date = dt
        self.selected_date_str = self.date_utils.format(dt)
        self.current_date_label.config(text=dt.strftime("%Y.%m.%d"))
        note = self.data_mgr.get(self.selected_date_str)
        self.text_area.delete("1.0", tk.END)
        if note:
            self.text_area.insert("1.0", note)

    def _save_and_select(self, new_date):
        self.save_note()
        self._select_date(new_date)

    def prev_day(self):
        self._save_and_select(self.selected_date - timedelta(days=1))

    def next_day(self):
        self._save_and_select(self.selected_date + timedelta(days=1))

    def go_to_today(self):
        self._save_and_select(date.today())

    # -----------------------------------------------------
    # DATA OPERATIONS
    # -----------------------------------------------------
    @run_ui_with_error_handling
    def save_note(self, event=None):
        content = self.text_area.get("1.0", tk.END)
        clean_content = content.strip()
        final_content = clean_content + "\n" if clean_content else ""
        if self.data_mgr.get(self.selected_date_str) != final_content:
            self.data_mgr.set(self.selected_date_str, final_content)
            self.data_mgr.save()

    @run_ui_with_error_handling
    def clear_note(self):
        if messagebox.askyesno("Confirm Clear",
                                f"Clear notes for {self.selected_date_str}?"):
            self.data_mgr.clear(self.selected_date_str)
            self.data_mgr.save()
            self.text_area.delete("1.0", tk.END)

    @run_ui_with_error_handling
    def goto_date(self):
        date_str = simpledialog.askstring(
            "Go to Specific Day", "Enter a date (YYYY-MM-DD):",
            initialvalue=self.selected_date_str, parent=self
        )
        if not date_str:
            return
        dt = self.date_utils.parse(date_str.strip())
        if dt:
            self._save_and_select(dt)
        else:
            messagebox.showerror("Invalid Date",
                                 "Please enter a valid date in format YYYY-MM-DD.")

    @run_ui_with_error_handling
    def export_notes(self):
        folder = filedialog.askdirectory(title="Select Folder to Export Notes")
        if not folder:
            return
        try:
            for date_str, note in self.data_mgr.data.items():
                clean_note = note.strip()
                export_content = clean_note + "\n" if clean_note else ""
                filename = f"{date_str.replace(':', '-')}.txt"
                path = os.path.join(folder, filename)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(export_content)
            messagebox.showinfo("Export Complete",
                                f"Notes exported to:\n{folder}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    # -----------------------------------------------------
    # EXIT HANDLING
    # -----------------------------------------------------
    def on_close(self):
        self.save_note()
        self.destroy()

# =========================================================
# MAIN ENTRY
# =========================================================
def main():
    DiaryUI().mainloop()

if __name__ == "__main__":
    main()
