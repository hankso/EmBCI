#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tests/test_ili9341.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sat 23 Feb 2019 13:47:11 CST

'''Test GUI is not a good idea.'''

# built-in
import os

# requirements.txt: data-processing: numpy
import numpy as np
import pytest

pytest.skip('skip embedded device only tests', allow_module_level=True)

from embci.configs import BASEDIR
from embci.utils import get_config
from embci.utils.ili9341_api import ILI9341_API, rgb888to565, rgb24to565
from embci.utils.ili9341_api import (
    ILI9341_WHITE, ILI9341_GREEN, ILI9341_BLUE, ILI9341_CYAN,
    ILI9341_YELLOW, ILI9341_RED, ILI9341_MAGENTA)


@pytest.fixture(scope='module')
def ili9341():
    ili = ILI9341_API(
        dc=get_config('PIN_ILI9341_DC', 2),
        rst=get_config('PIN_ILI9341_RST', None))
    device = (get_config('DEV_ESP32_SPI_BUS', 1),
              get_config('DEV_ESP32_SPI_CS', 1))
    ili.open(device)
    ili.start()
    yield ili
    ili.close()


def test_setfont(ili9341):
    ili9341.setfont(
        os.path.join(BASEDIR, 'files', 'fonts', 'yahei_mono.ttf'))


def test_draw_basic(ili9341):
    for i in range(240):
        ili9341.draw_point(i, i, [int(i / 240.0 * 0xff)] * 2)
    ili9341.draw_line(239, 0, 0, 239, ILI9341_WHITE)
    ili9341.draw_rect(10, 20, 20, 30, ILI9341_GREEN)
    ili9341.draw_rectf(10, 35, 20, 45, ILI9341_BLUE)
    ili9341.draw_circle(30, 50, 10, ILI9341_CYAN)
    ili9341.draw_circlef(30, 75, 14, ILI9341_YELLOW)
    ili9341.draw_round(100, 100, 15, ILI9341_RED, 0)
    ili9341.draw_round(100, 100, 15, ILI9341_MAGENTA, 1)
    ili9341.draw_round(100, 100, 15, ILI9341_GREEN, 2)
    ili9341.draw_round(100, 100, 15, ILI9341_WHITE, 3)


def test_draw_round_rectf(ili9341):
    tiffany_blue = [0x0A, 0xBA, 0xB5]
    ili9341.draw_round_rectf(
        150, 120, 300, 220, 7, rgb888to565(*tiffany_blue))


def test_draw_text(ili9341):
    for i in range(5):
        x, y = np.random.randint(0, 200, 2)
        c = np.random.randint(0xffffff)
        ili9341.draw_text(x, y, 'EmBCI', rgb24to565(c))
