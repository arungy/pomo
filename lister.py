try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    import sys
    print("Tkinter not found. Please install it (e.g., 'sudo apt install python3-tk') and rerun.")
    sys.exit(1)

import json
import os
import sys
import uuid
import tempfile
import shutil
from typing import Optional

# Determine storage path relative to executable or script
if getattr(sys, "frozen", False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

STORAGE_FILE = os.path.join(base_path, "tasklogs.json")

# Constants
COLOR_COMPLETED = "#808080"
COLOR_DIVIDER = "#0000FF"
COLOR_TODAY = "#008000"  # green for tasks marked for today
FONT_NORMAL = ("TkDefaultFont", 14)

class Task:
    def __init__(self, text: str, completed: bool = False, for_today: bool = False, id: Optional[str] = None):
        self.text = text
        self.completed = completed
        self.for_today = for_today
        self.id = id or str(uuid.uuid4())

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "completed": self.completed,
            "for_today": self.for_today,
        }

    @staticmethod
    def from_dict(d):
        return Task(
            d["text"],
            d.get("completed", False),
            d.get("for_today", False),
            d.get("id"),
        )

class TaskManager:
    def __init__(self):
        self.tasks = []

    def load(self):
        if not os.path.exists(STORAGE_FILE):
            return
        try:
            with open(STORAGE_FILE, encoding="utf-8") as f:
                self.tasks = [Task.from_dict(t) for t in json.load(f) if "text" in t]
        except Exception as e:
            messagebox.showwarning("Load Error", f"Failed to load tasks:\n{e}")

    def save(self):
        try:
            dir_name = os.path.dirname(STORAGE_FILE)
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dir_name, delete=False) as tf:
                json.dump([t.to_dict() for t in self.tasks], tf, indent=2)
            shutil.move(tf.name, STORAGE_FILE)
        except Exception as e:
            messagebox.showwarning("Save Error", f"Failed to save tasks:\n{e}")

    def add(self, text: str) -> Optional[Task]:
        if any(t.text == text for t in self.tasks):
            return None
        task = Task(text)
        self.tasks.append(task)
        return task

    def update_text(self, task: Task, new_text: str) -> bool:
        if any(t.text == new_text and t.id != task.id for t in self.tasks):
            return False
        task.text = new_text
        return True

    def delete(self, task: Task):
        self.tasks = [t for t in self.tasks if t.id != task.id]

    def toggle_completed(self, task: Task):
        task.completed = not task.completed

    def toggle_for_today(self, task: Task):
        task.for_today = not task.for_today

class SimpleTaskUI:
    def __init__(self, root):
        self.root = root
        self.manager = TaskManager()
        self.manager.load()
        self.editing_task: Optional[Task] = None
        self.show_only_today = True

        root.title("Lister")

        window_width, window_height = 800, 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.minsize(window_width, window_height)

        self.entry = tk.Entry(root, font=FONT_NORMAL)
        self.entry.pack(padx=10, pady=10, fill="x")
        self.entry.bind("<Return>", self.on_entry_return)
        self.entry.bind("<Escape>", self.cancel_edit)

        self.filter_btn = tk.Button(root, text="Show All Tasks", command=self.toggle_filter)
        self.filter_btn.pack(padx=10, pady=(0, 10), fill="x")

        self.listbox = tk.Listbox(root, font=FONT_NORMAL, activestyle="none", selectmode=tk.SINGLE)
        self.listbox.pack(padx=10, pady=5, fill="both", expand=True)
        self.listbox.bind("<Double-1>", self.start_edit_task)
        self.listbox.bind("<Delete>", self.delete_task)
        self.listbox.bind("<space>", self.toggle_task_completed)

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Toggle For Today", command=self.toggle_for_today_selected_task)
        self.listbox.bind("<Button-3>", self.show_context_menu)  # Right-click Windows/Linux
        self.listbox.bind("<Control-Button-1>", self.show_context_menu)  # Ctrl+Click macOS

        self.refresh()

    def toggle_filter(self):
        self.show_only_today = not self.show_only_today
        self.filter_btn.config(
            text="Show All Tasks" if self.show_only_today else "Show Today's Tasks"
        )
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)

        tasks = self.manager.tasks
        if self.show_only_today:
            tasks = [t for t in tasks if t.for_today]

        today_tasks = [t for t in tasks if t.for_today and not t.completed]
        non_today_tasks = [t for t in tasks if not t.for_today and not t.completed]
        completed = [t for t in tasks if t.completed]

        for t in today_tasks:
            idx = self.listbox.size()
            self.listbox.insert(tk.END, t.text)
            self.listbox.itemconfig(idx, fg=COLOR_TODAY)

        for t in non_today_tasks:
            self.listbox.insert(tk.END, t.text)

        if (today_tasks or non_today_tasks) and completed:
            idx = self.listbox.size()
            self.listbox.insert(tk.END, "----- Completed Tasks -----")
            self.listbox.itemconfig(idx, fg=COLOR_DIVIDER)

        for t in completed:
            idx = self.listbox.size()
            display_text = t.text + " ✔"
            self.listbox.insert(tk.END, display_text)
            self.listbox.itemconfig(idx, fg=COLOR_TODAY if t.for_today else COLOR_COMPLETED)

    def get_task_by_index(self, idx: int) -> Optional[Task]:
        tasks = self.manager.tasks
        if self.show_only_today:
            tasks = [t for t in tasks if t.for_today]

        today_tasks = [t for t in tasks if t.for_today and not t.completed]
        non_today_tasks = [t for t in tasks if not t.for_today and not t.completed]
        completed = [t for t in tasks if t.completed]

        divider_idx = -1
        if (today_tasks or non_today_tasks) and completed:
            divider_idx = len(today_tasks) + len(non_today_tasks)

        if idx == divider_idx:
            return None  # Divider selected

        if idx > divider_idx and divider_idx != -1:
            idx -= 1

        combined = today_tasks + non_today_tasks + completed
        if 0 <= idx < len(combined):
            return combined[idx]
        return None

    def get_selected_task(self) -> Optional[Task]:
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Selection Error", "Please select a task first.")
            return None
        return self.get_task_by_index(sel[0])

    def on_entry_return(self, event=None):
        text = self.entry.get().strip()
        if not text:
            messagebox.showinfo("Input Error", "Task text cannot be empty.")
            return

        if self.editing_task:
            if not self.manager.update_text(self.editing_task, text):
                messagebox.showinfo("Duplicate Task", "Task already exists.")
                return
            self.editing_task = None
        else:
            if not self.manager.add(text):
                messagebox.showinfo("Duplicate Task", "Task already exists.")
                return

        self.manager.save()
        self.entry.delete(0, tk.END)
        self.refresh()

    def start_edit_task(self, event=None):
        task = self.get_selected_task()
        if task:
            self.editing_task = task
            self.entry.delete(0, tk.END)
            self.entry.insert(0, task.text)
            self.entry.focus()
            self.entry.select_range(0, tk.END)

    def cancel_edit(self, event=None):
        if self.editing_task:
            self.editing_task = None
            self.entry.delete(0, tk.END)

    def delete_task(self, event=None):
        task = self.get_selected_task()
        if task and messagebox.askyesno("Delete Task", f"Delete selected task?\n\n{task.text}"):
            self.manager.delete(task)
            self.manager.save()
            self.refresh()

    def toggle_task_completed(self, event=None):
        task = self.get_selected_task()
        if task:
            self.manager.toggle_completed(task)
            self.manager.save()
            self.refresh()

    def toggle_for_today_selected_task(self):
        task = self.get_selected_task()
        if task:
            self.manager.toggle_for_today(task)
            self.manager.save()
            self.refresh()

    def show_context_menu(self, event):
        if self.listbox.curselection():
            self.menu.tk_popup(event.x_root, event.y_root)

def main():
    root = tk.Tk()
    SimpleTaskUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
