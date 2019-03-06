#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/constants.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 05 Feb 2019 17:01:54 CST

'''Define some constants here'''

__all__ = []

# ===============================================================================
# command dicts

command_dict_null = {'_desc': 'This is an empty command dict'}

command_dict_plane = {
    'left':       ['3', 0.5],
    'right':      ['4', 0.5],
    'up':         ['1', 0.5],
    'down':       ['2', 0.5],
    'disconnect': ['9', 0.5],
    '_desc':     ("plane war game support command:\n\t"
                  "left, right, up, down, disconnect")}

command_dict_glove_box = {
    'thumb':        ['1', 0.5],
    'index':        ['2', 0.5],
    'middle':       ['3', 0.5],
    'ring':         ['5', 0.5],
    'little':       ['4', 0.5],
    'grab-all':     ['6', 0.5],
    'relax':        ['7', 0.5],
    'grab':         ['8', 0.5],
    'thumb-index':  ['A', 0.5],
    'thumb-middle': ['B', 0.5],
    'thumb-ring':   ['C', 0.5],
    'thumb-little': ['D', 0.5],
    '_desc':       ("This is a dict for glove box version 1.0.\n"
                    "Support command:\n\t"
                    "thumb, index, middle, ring\n\t"
                    "little, grab-all, relax, grab\n")}

command_dict_arduino_screen_v1 = {
    'point':  ['#0\r\n{x},{y}\r\n', 0.5],
    'line':   ['#1\r\n{x1},{y1},{x2},{y2}\r\n', 0.5],
    'circle': ['#2\r\n{x},{y},{r}\r\n', 0.5],
    'rect':   ['#3\r\n{x1},{y1},{x2},{y2}\r\n', 0.5],
    'text':   ['#4\r\n{x},{y},{s}\r\n', 0.5],
    'clear':  ['#5\r\n', 1.0],
    '_desc': ("Arduino-controlled SSD1306 0.96' 128x64 OLED screen v1.0:\n"
              "you need to pass in args as `key`=`value`(dict)\n\n"
              "Commands | Args\n"
              "point    | x, y\n"
              "line     | x1, y1, x2, y2\n"
              "circle   | x, y, r\n"
              "rect     | x1, y1, x2, y2\n"
              "text     | x, y, s\n")}

command_dict_arduino_screen_v2 = {
    'points': ['P{:c}{}', 0.1],
    'point':  ['D{:c}{}', 0.05],
    'text':   ['S{:c}{:s}', 0.1],
    'clear':  ['C', 0.5],
    '_desc': ("Arduino-controlled ILI9325D 2.3' 220x176 LCD screen v1.0:\n"
              "Commands | Args\n"
              "points   | len(pts), bytearray([y for x, y in pts])\n"
              "point    | len(pts), bytearray(np.uint8(pts).reshape(-1))\n"
              "text     | len(str), str\n"
              "clear    | no args, clear screen\n")}

command_dict_uart_screen_winbond_v1 = {
    'point':   ['PS({x},{y},{c});\r\n', 0.38/220],
    'line':    ['PL({x1},{y1},{x2},{y2},{c});\r\n', 3.5/220],
    'circle':  ['CIR({x},{y},{r},{c});\r\n', 3.0/220],
    'circlef': ['CIRF({x},{y},{r},{c});\r\n', 8.0/220],
    'rect':    ['BOX({x1},{y1},{x2},{y2},{c});\r\n', 3.0/220],
    'rrect':   ['BOX({x1},{y1},{x2},{y2},{c});\r\n', 3.0/220],
    'rectf':   ['BOXF({x1},{y1},{x2},{y2},{c});\r\n', 15.0/220],
    'rrectf':  ['BOXF({x1},{y1},{x2},{y2},{c});\r\n', 15.0/220],
    'text':    ['DC16({x},{y},{s},{c});\r\n', 15.0/220],
    'dir':     ['DIR({:d});\r\n', 3.0/220],
    'clear':   ['CLR(0);\r\n', 10.0/220],
    '_desc':  ("UART-controlled Winbond 2.3' 220x176 LCD screen:\n"
               "Commands | Args\n"
               "point    | x, y, c\n"
               "line     | x1, y1, x2, y2, c\n"
               "circle   | x, y, r, c\n"
               "circlef  | x, y, r, c, filled circle\n"
               "rect     | x1, y1, x2, y2, c\n"
               "rectf    | x1, y1, x2, y2, c, filled rectangle\n"
               "text     | x, y, s(string), c(color)\n"
               "dir      | one num, 0 means vertical, 1 means horizental\n"
               "clear    | clear screen will black\n")}

command_dict_esp32 = {
    'start':     ['', 0.2],
    'write':     ['', 0.3],
    'writereg':  ['', 0.5],
    'writeregs': ['', 0.5],
    'readreg':   ['', 0.5],
    'readregs':  ['', 0.5],
    '_desc':    ("This dict is used to commucate with onboard ESP32.\n"
                 "Supported command:\n\t"
                 "start: init ads1299 and start RDATAC mode\n\t"
                 "write: nothing\n\t"
                 "writereg: write single register\n\t"
                 "writeregs: write a list of registers\n\t"
                 "readreg: read single register\n\t"
                 "readregs: read a list of registers\n\t")}

__all__ += ['command_dict_' + _ for _ in
            ['null', 'plane', 'glove_box', 'arduino_screen_v1',
             'arduino_screen_v2', 'uart_screen_winbond_v1', 'esp32']]

# =============================================================================
# Colors

BASIC_COLOR_NAMES = [
    'black', 'red', 'green', 'blue', 'yellow', 'cyan', 'purple', 'gray',
    'grey', 'brown', 'orange', 'pink', 'white',
]

RGB888_BLACK    = (  0,   0,   0)  # noqa: E201
RGB888_BLUE     = (  0,   0, 255)  # noqa: E201
RGB888_GREEN    = (  0, 255,   0)  # noqa: E201
RGB888_CYAN     = (  0, 255, 255)  # noqa: E201
RGB888_RED      = (255,   0,   0)  # noqa: E221
RGB888_MAGENTA  = (255,   0, 255)  # noqa: E221
RGB888_YELLOW   = (255, 255,   0)  # noqa: E221
RGB888_WHITE    = (255, 255, 255)  # noqa: E221
RGB888_PURPLE   = (128,   0, 128)  # noqa: E221
RGB888_ORANGE   = (255, 160,  10)  # noqa: E221
RGB888_GREY     = (128, 128, 128)  # noqa: E221
RGB888_GRAY     = (200, 200, 200)  # noqa: E221

RGB565_BLACK    = [0x00, 0x00]  # noqa: E221
RGB565_BLUE     = [0x00, 0x1F]  # noqa: E221
RGB565_GREEN    = [0x07, 0xE0]  # noqa: E221
RGB565_CYAN     = [0x07, 0xFF]  # noqa: E221
RGB565_RED      = [0xF8, 0x00]  # noqa: E221
RGB565_MAGENTA  = [0xF8, 0x1F]  # noqa: E221
RGB565_YELLOW   = [0xFF, 0xE0]  # noqa: E221
RGB565_WHITE    = [0xFF, 0xFF]  # noqa: E221
RGB565_PURPLE   = [0x41, 0x2B]  # noqa: E221
RGB565_ORANGE   = [0xFD, 0xC0]  # noqa: E221
RGB565_GREY     = [0x84, 0x10]  # noqa: E221
RGB565_GRAY     = [0xCE, 0x59]  # noqa: E221

colormapper_default = {}
for c in BASIC_COLOR_NAMES:
    color = locals().get('RGB888_' + c.upper())
    if color is None:
        continue
    colormapper_default[c] = color
del c, color

colormapper_uart_screen_winbond_v1 = {}
for n, c in enumerate(BASIC_COLOR_NAMES):
    colormapper_uart_screen_winbond_v1[c] = n
del n, c

colormapper_spi_screen_ili9341 = {}
for c in BASIC_COLOR_NAMES:
    color = locals().get('RGB565_' + c.upper())
    if color is None:
        continue
    colormapper_spi_screen_ili9341[c] = color
del c, color

__all__ += ['colormapper_' + _ for _ in
            ['default', 'uart_screen_winbond_v1', 'spi_screen_ili9431']]

# =============================================================================
# Misc

BOOLEAN_TABLE = {
    u'0': False, u'1': True,
    u'No': False, u'Yes': True,
    u'Off': False, u'On': True,
    u'False': False, u'True': True,
    u'None': None,
}

__all__ += ['BOOLEAN_TABLE']

# THE END
