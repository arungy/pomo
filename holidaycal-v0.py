#!/usr/bin/env python3

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import datetime

def cal_show_background(pygame, display_window, width, height, block_size_w, block_size_h, colour):
    pygame.draw.rect(display_window, colour, [width, height, block_size_w - 4, block_size_h - 4])


def cal_show_message(display_window, font_style, msg, colour, width, height):
    message = font_style.render(msg, True, colour)
    display_window.blit(message, [width, height])


def cal_release(pygame):
    pygame.quit()


def find_year_start_day(year):
    day = datetime.datetime.strptime(str(year) + '.01.01', '%Y.%m.%d')
    return ((day.isoweekday() % 7) + 1)         # sun: 1, mon: 2, ... Sat: 7


def calc_month_days(month_num_days, start_day):
    days_in_month = []
    num_days = 42
    start_day_minus1 = start_day - 1
    next_date_slot = 1

    for date_slot in range(0, num_days):
        word = ''
        if date_slot >= (start_day_minus1) and date_slot < (month_num_days + start_day_minus1):
            date = date_slot - start_day_minus1 + 1
            next_date_slot = ((date_slot + 1) % 7) + 1
            word = '{:3d}'.format(date)
        else:
            word = '{:3s}'.format('')

        days_in_month.append(word)

    return (next_date_slot, days_in_month)


def calc_holiday_in():
    holiday_in = [  [1, 14       ], [      ], [31                ],  # jan, feb, mar
                    [18          ], [1     ], [                  ],  # apr, may, jun
                    [            ], [15, 27], [                  ],  # jul, aug, sep
                    [1, 2, 20, 22], [      ], [25, 26, 29, 30, 31]   # oct, nov, dec
    ]

    holiday_str = []
    for mh in holiday_in:
        mon_list_str = []
        for d in mh:
            tmp_str = '{:3d}'.format(d)
            mon_list_str.append(tmp_str)
        holiday_str.append(mon_list_str)

    return holiday_str


def calc_holiday_jp():
    holiday_jp = [  [1, 2, 3, 13 ], [11, 24    ], [20    ],  # jan, feb, mar
                    [29          ], [3, 5, 6   ], [      ],  # apr, may, jun
                    [21          ], [11, 14, 15], [15, 23],  # jul, aug, sep
                    [13          ], [3, 24     ], [30, 31]   # oct, nov, dec
    ]

    holiday_str = []
    for mh in holiday_jp:
        mon_list_str = []
        for d in mh:
            tmp_str = '{:3d}'.format(d)
            mon_list_str.append(tmp_str)
        holiday_str.append(mon_list_str)
    return holiday_str


def calc_weekdays():
    days = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

    row_days = ''
    for d in range(0, 7):
        row_days += ' {:2s}'.format(days[d])

    print('{}  {}  {}'.format(row_days, row_days, row_days))


def display_month(month):
    for m in month:
        print(m)


def print_quarter(month1, month2, month3):
    max_len = max(len(month1), len(month2), len(month3))

    empty_row = ''
    for n in range(0, 7):
        empty_row += '{:3s}'.format('')

    for n in range(len(month1), max_len):
        month1.append(empty_row)

    for n in range(len(month2), max_len):
        month2.append(empty_row)

    for n in range(len(month3), max_len):
        month3.append(empty_row)

    calc_weekdays()
    for m1,m2,m3 in zip(month1, month2, month3):
        print('{}  {}  {}'.format(m1, m2, m3))
    print()


def show_calendar():
    CLR_WHITE  = 0
    CLR_BLACK  = 1
    CLR_RED    = 2
    CLR_GREEN  = 3
    CLR_BLUE   = 4
    CLR_YELLOW = 5
    CLR_ORANGE = 7
    CLR_MAX    = 8

    colours = [None] * CLR_MAX
    colours[CLR_WHITE]  = (255, 255, 255)
    colours[CLR_BLACK]  = (0, 0, 0)
    colours[CLR_RED]    = (213, 50, 80)
    colours[CLR_GREEN]  = (0,187,119)
    colours[CLR_BLUE]   = (50, 153, 213)
    colours[CLR_YELLOW] = (255,237,41)
    colours[CLR_ORANGE] = (242, 140, 40)

    WIDTH = 620
    HEIGHT = 700
    CAL_YEAR = 2025  #int(datetime.date.today().strftime('%Y'))

    cal_display = True

    # init game
    pygame.init()
    pygame.display.set_caption('Calendar ' + str(CAL_YEAR))

    font_style = pygame.font.SysFont('bahnschrift', 15)

    display_window = pygame.display.set_mode((WIDTH, HEIGHT))
    display_window.fill(colours[CLR_WHITE])

    clock = pygame.time.Clock()

    days = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
    month_start_day = find_year_start_day(CAL_YEAR)

    (month_start_day, jan_dates) = calc_month_days(31, month_start_day)
    (month_start_day, feb_dates) = calc_month_days(29 if ((CAL_YEAR % 4) == 0) else 28, month_start_day)
    (month_start_day, mar_dates) = calc_month_days(31, month_start_day)

    (month_start_day, apr_dates) = calc_month_days(30, month_start_day)
    (month_start_day, may_dates) = calc_month_days(31, month_start_day)
    (month_start_day, jun_dates) = calc_month_days(30, month_start_day)

    (month_start_day, jul_dates) = calc_month_days(31, month_start_day)
    (month_start_day, aug_dates) = calc_month_days(31, month_start_day)
    (month_start_day, sep_dates) = calc_month_days(30, month_start_day)

    (month_start_day, oct_dates) = calc_month_days(31, month_start_day)
    (month_start_day, nov_dates) = calc_month_days(30, month_start_day)
    (month_start_day, dec_dates) = calc_month_days(31, month_start_day)


    month_names = [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    year_dates = [jan_dates, feb_dates, mar_dates, apr_dates, may_dates, jun_dates,
                  jul_dates, aug_dates, sep_dates, oct_dates, nov_dates, dec_dates]

    holiday_in = calc_holiday_in()
    holiday_jp = calc_holiday_jp()

    block_size_w = 25
    block_size_h = 20

    row_height = 10
    col_num = 0

    for month in range(0, len(year_dates), 3):
        month_colour = colours[CLR_RED]
        cal_show_message(display_window, font_style, month_names[month + 0].upper(), month_colour, 90 + (0 * 200), row_height)
        cal_show_message(display_window, font_style, month_names[month + 1].upper(), month_colour, 90 + (1 * 200), row_height)
        cal_show_message(display_window, font_style, month_names[month + 2].upper(), month_colour, 90 + (2 * 200), row_height)
        row_height += block_size_h

        for d in range(0, len(days)):
            day_colour = colours[CLR_GREEN]
            day_name = '{:3s}'.format(days[d])
            cal_show_message(display_window, font_style, day_name, day_colour,  20 + (0 * 200) + (d * block_size_w), row_height)
            cal_show_message(display_window, font_style, day_name, day_colour,  20 + (1 * 200) + (d * block_size_w), row_height)
            cal_show_message(display_window, font_style, day_name, day_colour,  20 + (2 * 200) + (d * block_size_w), row_height)

        row_height += block_size_h

        m1 = month + 0
        m2 = month + 1
        m3 = month + 2
        m1_inhol_len = len(holiday_in[m1])
        m2_inhol_len = len(holiday_in[m2])
        m3_inhol_len = len(holiday_in[m3])
        m1_inhol_num = 0
        m2_inhol_num = 0
        m3_inhol_num = 0

        m1_jphol_len = len(holiday_jp[m1])
        m2_jphol_len = len(holiday_jp[m2])
        m3_jphol_len = len(holiday_jp[m3])
        m1_jphol_num = 0
        m2_jphol_num = 0
        m3_jphol_num = 0

        for idx in range(len(year_dates[0])):
            m1_colour = CLR_WHITE
            m2_colour = CLR_WHITE
            m3_colour = CLR_WHITE

            if m1_inhol_len > 0 and m1_inhol_num < m1_inhol_len:
                if holiday_in[m1][m1_inhol_num] == year_dates[m1][idx]:
                    m1_colour = CLR_ORANGE
                    m1_inhol_num += 1

            if m2_inhol_len > 0 and m2_inhol_num < m2_inhol_len:
                if holiday_in[m2][m1_inhol_num] == year_dates[m2][idx]:
                    m2_colour = CLR_ORANGE
                    m2_inhol_num += 1

            if m3_inhol_len > 0 and m3_inhol_num < m3_inhol_len:
                if holiday_in[m3][m3_inhol_num] == year_dates[m3][idx]:
                    m3_colour = CLR_ORANGE
                    m3_inhol_num += 1


            if m1_jphol_len > 0 and m1_jphol_num < m1_jphol_len:
                if (holiday_jp[m1][m1_jphol_num] == year_dates[m1][idx]):
                    m1_colour = CLR_YELLOW if m1_colour == CLR_ORANGE else CLR_BLUE
                    m1_jphol_num += 1

            if m2_jphol_len > 0 and m2_jphol_num < m2_jphol_len:
                if (holiday_jp[m2][m2_jphol_num] == year_dates[m2][idx]):
                    m2_colour = CLR_YELLOW if m2_colour == CLR_ORANGE else CLR_BLUE
                    m2_jphol_num += 1

            if m3_jphol_len > 0 and m3_jphol_num < m3_jphol_len:
                if (holiday_jp[m3][m3_jphol_num] == year_dates[m3][idx]):
                    m3_colour = CLR_YELLOW if m3_colour == CLR_ORANGE else CLR_BLUE
                    m3_jphol_num += 1

            cal_show_background(pygame, display_window, (20 + (0 * 200) + (col_num * block_size_w)), row_height, block_size_w, block_size_h, colours[m1_colour])
            cal_show_background(pygame, display_window, (20 + (1 * 200) + (col_num * block_size_w)), row_height, block_size_w, block_size_h, colours[m2_colour])
            cal_show_background(pygame, display_window, (20 + (2 * 200) + (col_num * block_size_w)), row_height, block_size_w, block_size_h, colours[m3_colour])


            cal_show_message(display_window, font_style, year_dates[m1][idx], colours[CLR_BLACK],  20 + (0 * 200) + (col_num * block_size_w), row_height)
            cal_show_message(display_window, font_style, year_dates[m2][idx], colours[CLR_BLACK],  20 + (1 * 200) + (col_num * block_size_w), row_height)
            cal_show_message(display_window, font_style, year_dates[m3][idx], colours[CLR_BLACK],  20 + (2 * 200) + (col_num * block_size_w), row_height)
            col_num += 1

            if (idx % 7) == 6:
                col_num = 0
                row_height += block_size_h

        row_height += 6

    label_row_width = 80
    cal_show_background(pygame, display_window, label_row_width,       row_height, 45, block_size_h, colours[CLR_ORANGE])
    cal_show_background(pygame, display_window, label_row_width + 50,  row_height, 45, block_size_h, colours[CLR_BLUE])
    cal_show_background(pygame, display_window, label_row_width + 100, row_height, 45, block_size_h, colours[CLR_YELLOW])


    cal_show_message(display_window, font_style, 'Holiday: ', colours[CLR_BLACK],  20,                    row_height)
    cal_show_message(display_window, font_style, 'India',     colours[CLR_BLACK],  label_row_width,       row_height)
    cal_show_message(display_window, font_style, 'Japan',     colours[CLR_BLACK],  label_row_width + 50,  row_height)
    cal_show_message(display_window, font_style, 'Both',      colours[CLR_BLACK],  label_row_width + 100, row_height)

    while cal_display:
        for event in pygame.event.get():
            if (event.type == pygame.QUIT) or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                cal_display = False

        pygame.display.update()
        clock.tick(30)

    cal_release(pygame)


def main():
    show_calendar()


if __name__ == '__main__':
    main()
