try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    import sys
    print("Tkinter not found. Install with: sudo apt install python3-tk")
    sys.exit(1)

import json, os, sys, uuid, tempfile, shutil, threading, time
from typing import Optional
from datetime import date

# ===================== CONFIG ====================
POMODORO_WORK_MINUTES = 25
POMODORO_BREAK_MINUTES = 5
COLOR_COMPLETED = "#808080"
COLOR_TODAY = "#008000"
FONT_NORMAL = ("TkDefaultFont", 14)
BASE_PATH = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
STORAGE_FILE = os.path.join(BASE_PATH, "listerlogs.json")

# ===================== MODEL =====================
class Task:
    def __init__(self, text, completed=False, for_today=False, id=None):
        self.text, self.completed, self.for_today, self.id = text, completed, for_today, id or str(uuid.uuid4())
    def to_dict(self):
        return {"id": self.id, "text": self.text, "completed": self.completed, "for_today": self.for_today}
    @staticmethod
    def from_dict(d):
        return Task(d["text"], d.get("completed", False), d.get("for_today", False), d.get("id"))

# ================== DATA/STORAGE =================
class TaskManager:
    def __init__(self):
        self.tasks: list[Task] = []
        self.pomodoro_stats: dict[str, int] = {}

    def load(self):
        if not os.path.exists(STORAGE_FILE): return
        try:
            with open(STORAGE_FILE, encoding="utf-8") as f:
                d = json.load(f)
                self.tasks = [Task.from_dict(t) for t in (d["tasks"] if isinstance(d, dict) else d) if "text" in t]
                if isinstance(d, dict): self.pomodoro_stats = d.get("pomodoro_stats", {})
        except Exception as e:
            messagebox.showwarning("Load Error", f"Failed to load tasks:\n{e}")

    def save(self):
        try:
            d = {"tasks": [t.to_dict() for t in self.tasks], "pomodoro_stats": self.pomodoro_stats}
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=os.path.dirname(STORAGE_FILE), delete=False) as tf:
                json.dump(d, tf, indent=2)
            shutil.move(tf.name, STORAGE_FILE)
        except Exception as e:
            messagebox.showwarning("Save Error", f"Failed to save tasks:\n{e}")

    def add(self, text):  # Returns None if duplicate
        if any(t.text == text for t in self.tasks): return None
        t = Task(text)
        self.tasks.append(t)
        return t

    def update_text(self, task, new_text):
        if any(t.text == new_text and t.id != task.id for t in self.tasks): return False
        task.text = new_text
        return True

    def delete(self, task): self.tasks = [t for t in self.tasks if t.id != task.id]
    def increment_pomodoro_today(self):
        d = str(date.today())
        self.pomodoro_stats[d] = self.pomodoro_stats.get(d, 0) + 1
    def get_pomodoro_today(self): return self.pomodoro_stats.get(str(date.today()), 0)

# ======================= UI ======================
class SimpleTaskUI:
    def __init__(self, root):
        self.root = root
        self.manager = TaskManager(); self.manager.load()
        self.editing_task: Optional[Task] = None
        self.show_only_today = True
        self.pomodoro_running = False
        self.pomodoro_time_left = 0
        self.pomodoro_phase = None
        self.setup_window(); self.create_widgets(); self.bind_shortcuts(); self.refresh()

    def setup_window(self):
        self.root.title("Lister")
        w, h = 800, 600
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h-200)//2}")
        self.root.minsize(w, h)

    def create_widgets(self):
        self.pomo_label = tk.Label(self.root, text="", font=FONT_NORMAL, fg="#AA0000")
        self.pomo_label.pack(padx=10, pady=2, fill="x")
        self.entry = tk.Entry(self.root, font=FONT_NORMAL)
        self.entry.pack(padx=10, pady=5, fill="x")
        self.entry.bind("<Return>", self.on_entry_return)
        self.entry.bind("<Escape>", lambda e: self.cancel_edit())
        self.filter_btn = tk.Button(self.root, text="Show All Tasks", command=self.toggle_filter)
        self.filter_btn.pack(padx=10, pady=(0, 10), fill="x")
        self.listbox = tk.Listbox(self.root, font=FONT_NORMAL, activestyle="none", selectmode=tk.SINGLE)
        self.listbox.pack(padx=10, pady=5, fill="both", expand=True)
        self.listbox.bind("<Double-1>", self.start_edit_task)
        self.listbox.bind("<Delete>", self.delete_task)
        self.listbox.bind("<space>", self.toggle_task_completed)
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Toggle for today", command=self.toggle_for_today_selected_task)
        self.menu.add_separator()
        self.menu.add_command(label="Show shortcuts", command=self.show_shortcuts)
        self.listbox.bind("<Button-3>", self.show_context_menu)
        self.listbox.bind("<Control-Button-1>", self.show_context_menu)

    def bind_shortcuts(self):
        self.root.bind("<Control-p>", lambda e: self.start_pomodoro())
        self.root.bind("<Control-s>", lambda e: self.stop_pomodoro())
        self.root.bind("<F1>", lambda e: self.show_shortcuts())

    def get_filtered_tasks(self):
        f = [t for t in self.manager.tasks if t.for_today] if self.show_only_today else self.manager.tasks
        today = [t for t in f if t.for_today and not t.completed]
        other = [t for t in f if not t.for_today and not t.completed]
        completed = [t for t in f if t.completed]
        return today, other, completed

    def refresh(self):
        self.listbox.delete(0, tk.END)
        today, other, completed = self.get_filtered_tasks()
        for t in today: self.listbox.insert(tk.END, t.text); self.listbox.itemconfig(self.listbox.size()-1, fg=COLOR_TODAY)
        for t in other: self.listbox.insert(tk.END, t.text)
        if (today or other) and completed:
            self.listbox.insert(tk.END, "─── Completed Tasks ───")
            self.listbox.itemconfig(self.listbox.size()-1, fg=COLOR_COMPLETED)
        for t in completed:
            self.listbox.insert(tk.END, t.text + " ✔")
            self.listbox.itemconfig(self.listbox.size()-1, fg=COLOR_COMPLETED)

    def get_task_by_index(self, idx):
        today, other, completed = self.get_filtered_tasks()
        div_idx = len(today)+len(other) if (today or other) and completed else -1
        if idx == div_idx: return None
        if div_idx != -1 and idx > div_idx: idx -= 1
        all_tasks = today + other + completed
        return all_tasks[idx] if 0 <= idx < len(all_tasks) else None

    def get_selected_task(self):
        sel = self.listbox.curselection()
        return self.get_task_by_index(sel[0]) if sel else None

    def on_entry_return(self, event=None):
        text = self.entry.get().strip()
        if not text:
            messagebox.showinfo("Input Error", "Task text cannot be empty."); return
        if self.editing_task:
            if not self.manager.update_text(self.editing_task, text):
                messagebox.showinfo("Duplicate Task", "Task already exists."); return
            self.editing_task = None
        else:
            if not self.manager.add(text):
                messagebox.showinfo("Duplicate Task", "Task already exists."); return
        self.manager.save(); self.entry.delete(0, tk.END); self.refresh()

    def start_edit_task(self, event=None):
        t = self.get_selected_task()
        if t:
            self.editing_task = t
            self.entry.delete(0, tk.END)
            self.entry.insert(0, t.text)
            self.entry.focus()
            self.entry.select_range(0, tk.END)

    def cancel_edit(self):
        self.editing_task = None; self.entry.delete(0, tk.END)

    def delete_task(self, event=None):
        t = self.get_selected_task()
        if t and messagebox.askyesno("Delete Task", f"Delete selected task?\n\n{t.text}"):
            self.manager.delete(t); self.manager.save(); self.refresh()

    def toggle_task_completed(self, event=None):
        t = self.get_selected_task()
        if t:
            t.completed = not t.completed
            self.manager.save(); self.refresh()

    def toggle_for_today_selected_task(self):
        t = self.get_selected_task()
        if t:
            t.for_today = not t.for_today
            self.manager.save(); self.refresh()

    def toggle_filter(self):
        self.show_only_today = not self.show_only_today
        self.filter_btn.config(text="Show All Tasks" if self.show_only_today else "Show Today's Tasks")
        self.refresh()

    def show_context_menu(self, event):
        if not self.listbox.curselection(): return
        t = self.get_selected_task()
        if t: self.menu.entryconfig(0, label="Toggle not for today" if t.for_today else "Toggle for today")
        self.menu.tk_popup(event.x_root, event.y_root)

    def show_shortcuts(self):
        messagebox.showinfo("Keyboard shortcuts", 
            "Ctrl+P : Start Pomodoro\nCtrl+S : Stop Pomodoro\nEnter  : Add/Edit\n"
            "Escape : Cancel editing\nDelete : Delete\nSpace  : Toggle completion\n"
            "Right Click : Toggle Today\nF1     : Help\n")

    def start_timer(self, phase, minutes):
        self.pomodoro_phase, self.pomodoro_time_left, self.pomodoro_running = phase, minutes*60, True
        self.update_pomodoro_label()
        threading.Thread(target=self._pomodoro_thread, daemon=True).start()

    def start_pomodoro(self):
        if not self.pomodoro_running: self.start_timer("work", POMODORO_WORK_MINUTES)

    def _pomodoro_thread(self):
        while self.pomodoro_time_left > 0 and self.pomodoro_running:
            time.sleep(1)
            self.pomodoro_time_left -= 1
            self.root.after(0, self.update_pomodoro_label)
        if self.pomodoro_running: self.root.after(0, self.next_phase)

    def next_phase(self):
        if self.pomodoro_phase == "work":
            self.manager.increment_pomodoro_today(); self.manager.save()
            if messagebox.askyesno("Pomodoro Complete", "Start your break now?"):
                self.start_timer("break", POMODORO_BREAK_MINUTES)
            else:
                self.stop_pomodoro()
        else:
            messagebox.showinfo("Break", "Break over! Back to work."); self.stop_pomodoro()

    def stop_pomodoro(self):
        self.pomodoro_running = False; self.pomodoro_phase = None
        self.update_pomodoro_label()

    def update_pomodoro_label(self):
        if not self.pomodoro_running:
            self.pomo_label.config(text=f"Pomodoros Today: {self.manager.get_pomodoro_today()}")
        else:
            mins, secs = divmod(self.pomodoro_time_left, 60)
            phase = "Pomodoro" if self.pomodoro_phase == "work" else "Break"
            self.pomo_label.config(text=f"{phase}: {mins:02d}:{secs:02d}")

# ====================== MAIN =====================
def main():
    root = tk.Tk()
    SimpleTaskUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
