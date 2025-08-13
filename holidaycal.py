import tkinter as tk
from tkinter import ttk
import datetime
import tkinter.font as tkfont

# --- Constants ---
FONT_FAMILY = "Arial"
FONT_SIZE = 10
CIRCLE_DIAMETER = int(FONT_SIZE * 2.4)

COLORS = {
    "today_fill": "green",
    "today_fg": "white",
    "india_fill": "orange",
    "japan_fill": "dodger blue",
    "both_fill": "yellow",
    "default_fg": "black",
    "japan_fg": "white",
    "empty_bg": "white"
}

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

DAYS_OF_WEEK = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]

# Hardcoded holiday data (month index: list of days)
HOLIDAYS_INDIA = {
    0: [1, 14], 1: [], 2: [31],
    3: [18], 4: [1], 5: [],
    6: [], 7: [15, 27], 8: [],
    9: [1, 2, 20, 22], 10: [], 11: [25, 26, 29, 30, 31]
}

HOLIDAYS_JAPAN = {
    0: [1, 2, 3, 13], 1: [11, 24], 2: [20],
    3: [29], 4: [3, 5, 6], 5: [],
    6: [21], 7: [11, 14, 15], 8: [15, 23],
    9: [13], 10: [3, 24], 11: [30, 31]
}


class YearCalendar(tk.Tk):
    def __init__(self, year, holidays_in=None, holidays_jp=None):
        super().__init__()

        self.resizable(False, False)  # Fix window size
        self.title(f"Calendar {year}")
        self.configure(bg=COLORS["empty_bg"])

        self.year = year
        self.holidays_in = holidays_in or {}
        self.holidays_jp = holidays_jp or {}

        self.today = datetime.date.today()

        # Fonts
        self.font_default = tkfont.Font(family=FONT_FAMILY, size=FONT_SIZE)
        self.font_bold = tkfont.Font(family=FONT_FAMILY, size=FONT_SIZE, weight="bold")

        # Container frame
        self.calendar_frame = ttk.Frame(self)
        self.calendar_frame.grid(padx=FONT_SIZE // 2, pady=FONT_SIZE // 2)

        self._build_calendar()
        self._center_window()

    def _build_calendar(self):
        # Clear frame
        for widget in self.calendar_frame.winfo_children():
            widget.destroy()

        columns = 4  # 4 columns per row

        for month_idx in range(12):
            # Month container frame
            frame = ttk.Frame(self.calendar_frame, borderwidth=1, relief="solid", padding=FONT_SIZE // 3)
            frame.grid(row=month_idx // columns, column=month_idx % columns,
                       padx=FONT_SIZE // 3, pady=FONT_SIZE // 3, sticky="nsew")

            # Month name label
            ttk.Label(frame, text=MONTHS[month_idx], font=self.font_bold).grid(row=0, column=0, columnspan=7, pady=(0, FONT_SIZE // 4))

            # Days of week header
            for col, day in enumerate(DAYS_OF_WEEK):
                tk.Label(frame, text=day, font=self.font_default).grid(row=1, column=col)

            # Calculate month start and days
            first_day = datetime.date(self.year, month_idx + 1, 1)
            start_index = (first_day.weekday() + 1) % 7  # Sunday=0

            if month_idx == 11:
                next_month = datetime.date(self.year + 1, 1, 1)
            else:
                next_month = datetime.date(self.year, month_idx + 2, 1)
            days_in_month = (next_month - datetime.timedelta(days=1)).day

            day = 1
            for week in range(5):  # max 5 weeks
                for weekday in range(7):
                    row = week + 2
                    col = weekday

                    if (week == 0 and weekday < start_index) or day > days_in_month:
                        self._create_empty_cell(frame, row, col)
                    else:
                        self._create_day_cell(frame, month_idx, day, row, col)
                        day += 1

        self._create_legend()

    def _create_empty_cell(self, parent, row, column):
        label = tk.Label(parent, text="   ", width=2, relief="flat", font=self.font_default,
                         bg=COLORS["empty_bg"])
        label.grid(row=row, column=column)

    def _create_day_cell(self, parent, month_idx, day_num, row, column):
        # Determine colors based on holidays and today
        in_india = day_num in self.holidays_in.get(month_idx, [])
        in_japan = day_num in self.holidays_jp.get(month_idx, [])
        is_today = (self.year == self.today.year and (month_idx + 1) == self.today.month and day_num == self.today.day)

        if is_today:
            fill = COLORS["today_fill"]
            fg = COLORS["today_fg"]
        elif in_india and in_japan:
            fill = COLORS["both_fill"]
            fg = COLORS["default_fg"]
        elif in_india:
            fill = COLORS["india_fill"]
            fg = COLORS["default_fg"]
        elif in_japan:
            fill = COLORS["japan_fill"]
            fg = COLORS["japan_fg"]
        else:
            fill = None
            fg = COLORS["default_fg"]

        canvas = tk.Canvas(parent, width=CIRCLE_DIAMETER, height=CIRCLE_DIAMETER,
                           highlightthickness=0, bg=COLORS["empty_bg"])
        if fill:
            r = CIRCLE_DIAMETER // 2 - 2
            x = y = CIRCLE_DIAMETER // 2
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline="")

        canvas.create_text(CIRCLE_DIAMETER // 2, CIRCLE_DIAMETER // 2,
                           text=str(day_num), fill=fg, font=self.font_default)
        canvas.grid(row=row, column=column)

    def _create_legend(self):
        legend_frame = ttk.Frame(self.calendar_frame, padding=FONT_SIZE // 3)
        legend_frame.grid(row=3, column=0, columnspan=4, pady=(FONT_SIZE // 2, FONT_SIZE // 3), sticky="w")

        legend_items = [
            (COLORS["india_fill"], "India holiday"),
            (COLORS["japan_fill"], "Japan holiday"),
            (COLORS["both_fill"], "Both holidays"),
            (COLORS["today_fill"], "Today")
        ]

        for i, (color, text) in enumerate(legend_items):
            color_label = tk.Label(legend_frame, background=color, width=2, height=1, relief="solid")
            color_label.grid(row=0, column=2 * i, padx=(0, FONT_SIZE // 4))
            text_label = tk.Label(legend_frame, text=text, font=self.font_default)
            text_label.grid(row=0, column=2 * i + 1, padx=(0, FONT_SIZE // 2))

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    app = YearCalendar(2025, HOLIDAYS_INDIA, HOLIDAYS_JAPAN)
    app.mainloop()
