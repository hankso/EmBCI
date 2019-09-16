#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/tests/drivers/test_ili9341.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-23 13:47:11

'''Testing GUI on screen devices is not a good idea.'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os

# requirements.txt: testing: pytest
# requirements.txt: data: numpy
import pytest
import numpy as np

pytest.skip('skip embedded device only tests', allow_module_level=True)

from embci.configs import DIR_SRC
from embci.utils import get_config
from embci.drives.ili9341 import (
    ILI9341_API, rgb888to565, rgb24to565,
    ILI9341_WHITE, ILI9341_GREEN, ILI9341_BLUE, ILI9341_CYAN,
    ILI9341_YELLOW, ILI9341_RED, ILI9341_MAGENTA
)


@pytest.fixture(scope='module')
def obj():
    ili = ILI9341_API(
        dc=get_config('PIN_ILI9341_DC', 2),
        rst=get_config('PIN_ILI9341_RST', None))
    device = (get_config('DEV_ESP32_SPI_BUS', 1),
              get_config('DEV_ESP32_SPI_CS', 1))
    ili.open(device)
    ili.start()
    yield ili
    ili.close()


def test_setfont(obj):
    obj.setfont(os.path.join(DIR_SRC, 'webui', 'fonts', 'YaHeiMono.ttf'))


def test_draw_basic(obj):
    for i in range(240):
        obj.draw_point(i, i, [int(i / 240.0 * 0xff)] * 2)
    obj.draw_line(239, 0, 0, 239, ILI9341_WHITE)
    obj.draw_rect(10, 20, 20, 30, ILI9341_GREEN)
    obj.draw_rectf(10, 35, 20, 45, ILI9341_BLUE)
    obj.draw_circle(30, 50, 10, ILI9341_CYAN)
    obj.draw_circlef(30, 75, 14, ILI9341_YELLOW)
    obj.draw_round(100, 100, 15, ILI9341_RED, 0)
    obj.draw_round(100, 100, 15, ILI9341_MAGENTA, 1)
    obj.draw_round(100, 100, 15, ILI9341_GREEN, 2)
    obj.draw_round(100, 100, 15, ILI9341_WHITE, 3)


def test_draw_round_rectf(obj):
    tiffany_blue = rgb888to565(0x0A, 0xBA, 0xB5)
    obj.draw_round_rectf(150, 120, 300, 220, 7, tiffany_blue)


def test_draw_text(obj):
    for i in range(5):
        x, y = np.random.randint(0, 200, 2)
        c = np.random.randint(0xffffff)
        obj.draw_text(x, y, 'EmBCI', rgb24to565(c))
