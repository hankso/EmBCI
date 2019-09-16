#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/drivers/ili9341.py
# Authors: Hank <hankso1106@gmail.com>
#          Tony DiCola <http://www.tonydicola.com>
# Create: 2019-05-23 02:16:40

'''
Modified ILI9341 python api based on Tony DiCola's Adafruit ILI9341 library.
'''

# built-ins
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import time
import threading

# requirements.txt: necessary: pillow
# requirements.txt: data: numpy
# requirements.txt: drivers: spidev, gpio4
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import spidev
from gpio4 import SysfsGPIO

__all__ = [
    'rgb888to565', 'rgb888to565_pro',
    'rgb565to888', 'rgb565to888_pro',
    'rgb24to565', 'rgb565to24',
    'ILI9341_API',
]


# ILI9341 registers
ILI9341_NOP         = 0x00
ILI9341_SWRESET     = 0x01
ILI9341_RDDID       = 0x04
ILI9341_RDDST       = 0x09
ILI9341_SLPIN       = 0x10
ILI9341_SLPOUT      = 0x11
ILI9341_PTLON       = 0x12
ILI9341_NORON       = 0x13
ILI9341_RDMODE      = 0x0A
ILI9341_RDMADCTL    = 0x0B
ILI9341_RDPIXFMT    = 0x0C
ILI9341_RDIMGFMT    = 0x0A
ILI9341_RDSELFDIAG  = 0x0F
ILI9341_INVOFF      = 0x20
ILI9341_INVON       = 0x21
ILI9341_GAMMASET    = 0x26
ILI9341_DISPOFF     = 0x28
ILI9341_DISPON      = 0x29
ILI9341_CASET       = 0x2A
ILI9341_PASET       = 0x2B
ILI9341_RAMWR       = 0x2C
ILI9341_RAMRD       = 0x2E
ILI9341_PTLAR       = 0x30
ILI9341_MADCTL      = 0x36
ILI9341_PIXFMT      = 0x3A
ILI9341_FRMCTR1     = 0xB1
ILI9341_FRMCTR2     = 0xB2
ILI9341_FRMCTR3     = 0xB3
ILI9341_INVCTR      = 0xB4
ILI9341_DFUNCTR     = 0xB6
ILI9341_PWCTR1      = 0xC0
ILI9341_PWCTR2      = 0xC1
ILI9341_PWCTR3      = 0xC2
ILI9341_PWCTR4      = 0xC3
ILI9341_PWCTR5      = 0xC4
ILI9341_VMCTR1      = 0xC5
ILI9341_VMCTR2      = 0xC7
ILI9341_RDID1       = 0xDA
ILI9341_RDID2       = 0xDB
ILI9341_RDID3       = 0xDC
ILI9341_RDID4       = 0xDD
ILI9341_GMCTRP1     = 0xE0
ILI9341_GMCTRN1     = 0xE1
ILI9341_PWCTR6      = 0xFC

# colors                               RED    G    B
ILI9341_BLACK       = [0x00, 0x00]  # (  0,   0,   0)
ILI9341_BLUE        = [0x00, 0x1F]  # (  0,   0, 255)
ILI9341_GREEN       = [0x07, 0xE0]  # (  0, 255,   0)
ILI9341_CYAN        = [0x07, 0xFF]  # (  0, 255, 255)
ILI9341_RED         = [0xF8, 0x00]  # (255,   0,   0)
ILI9341_MAGENTA     = [0xF8, 0x1F]  # (255,   0, 255)
ILI9341_YELLOW      = [0xFF, 0xE0]  # (255, 255,   0)
ILI9341_WHITE       = [0xFF, 0xFF]  # (255, 255, 255)
ILI9341_PURPLE      = [0x41, 0x2B]  # (128,   0, 128)
ILI9341_ORANGE      = [0xFD, 0xC0]  # (255, 160,  10)
ILI9341_GREY        = [0x84, 0x10]  # (128, 128, 128)

# rotation definition
ILI9341_MADCTL_MY   = 0x80
ILI9341_MADCTL_MX   = 0x40
ILI9341_MADCTL_MV   = 0x20
ILI9341_MADCTL_ML   = 0x10
ILI9341_MADCTL_RGB  = 0x00
ILI9341_MADCTL_BGR  = 0x08
ILI9341_MADCTL_MH   = 0x04


def rgb888to565(r, g, b):
    '''input r, g, b and output [chigh, clow]'''
    c = ((r & 0b11111000) << 8) | ((g & 0b11111100) << 3) | (b >> 3)
    return [c >> 8, c & 0xff]


def rgb888to565_pro(r, g, b):
    '''takes about 1.5x longer than normal rgb888to565, but more precise'''
    c = ((r * 249 + 1014) & 0xf800 |
         ((g * 253 + 505) >> 5) & 0xffe0 |
         (b * 249 + 1014) >> 11)
    return [c >> 8, c & 0xff]


def rgb565to888(ch, cl):
    '''input [chigh, clow] and output (r, g, b)'''
    r = ch & 0b11111000 | ((ch >> 3) & 0b00111)
    g = (ch & 0b111) << 5 | (cl & 0b11100000) >> 3 | (cl >> 5) & 0b011
    b = (cl & 0b11111) << 3 | cl & 0b00111
    return (r, g, b)


def rgb565to888_pro(ch, cl):
    '''takes about 1.4x longer than normal rgb565to888, but more precise'''
    r = ((ch >> 3) * 527 + 23) >> 6
    g = (((ch & 0b00000111) << 3 | cl >> 5) * 259 + 33) >> 6
    b = ((cl & 0b00011111) * 527 + 23) >> 6
    return (r, g, b)


def rgb24to565(v):
    '''input v between 0x000000 - 0xffffff and output [chigh, clow]'''
    return rgb888to565(v >> 16, v >> 8 & 0xff, v & 0xff)


def rgb565to24(ch, cl):
    '''input [chigh, clow] and output v between 0x000000 - 0xffffff'''
    r, g, b = rgb565to888(ch, cl)
    return r << 16 | g << 8 | b


class ILI9341_API(spidev.SpiDev):
    _lock = threading.Lock()

    def __init__(self, dc, rst=None, width=320, height=240, *a, **k):
        '''
        Create an interface of ILI9341 SPI Screen by establishing SPI
        connection through `/dev/spidev*.*`. GPIO number of D/C pin must be
        provided(more details about Data/Command pin in ILI9341 datasheet),
        as well as the spidev number(bus and cs pin). Reset pin is optional.

        Parameters
        ----------
        dev : tuple
            (bus, cs) indicating device `/dev/spidev${bus}.${cs}`
        dc : int
            Data/Command select pin number
        rst : int
            Reset pin number
        width, height : int
            screen width and height in pixel, default 320 x 240

        Notes
        -----
        Basic principle of this API:
            1. maintain a framebuffer (self.fb)
            2. draw on framebuffer (self.draw_*)
            3. render framebuffer to screen (self.flush)
        '''
        self._dc = SysfsGPIO(dc)
        if rst is None:
            self._rst = None
        else:
            self._rst = SysfsGPIO(rst)
        self._opened = False

        self.width = width
        self.height = height
        self.fb = np.zeros((self.height, self.width, 2), np.uint8)
        self.font = None
        self.size = 16

    def open(self, dev, max_speed_hz=25000000):
        assert not self._opened, 'already used spidev{}.{}'.format(*self._dev)
        super(ILI9341_API, self).open(dev[0], dev[1])
        self.max_speed_hz = max_speed_hz
        self.mode = 0
        self._dev = dev

        self._dc.export = True
        self._dc.direction = 'out'
        if self._rst is not None:
            self._rst.export = True
            self._rst.direction = 'out'
        self._opened = True

    def setfont(self, filename, size=None):
        size = size or self.size
        if self.font is None or self.font.path != filename:
            try:
                font = ImageFont.truetype(filename, size * 2)
                self.font = font
            except IOError:
                pass
        self.size = size

    def setsize(self, size):
        if self.font is None:
            print('[ILI9341 API] font not set yet!')
            return
        if self.size != size:
            self.font = ImageFont.truetype(self.font.path, size * 2)
            self.size = size

    def _command(self, data):
        '''Write an array of bytes to screen as command data'''
        self._dc.value = 0
        self.writebytes([data])

    def _data(self, data, chunk=4096):
        '''Write an array of bytes to screen as display data'''
        if len(data):
            self._dc.value = 1
            for s in range(0, len(data), chunk):
                self.xfer2(data[s:(s + chunk)])

    def _set_window(self, x1, y1, x2, y2):
        '''
        Set the pixel address window for proceeding drawing commands.
        x1 and x2 should define the minimum and maximum x pixel bounds.
        y1 and y2 should define the minimum and maximum y pixel bounds.
        If no parameters are specified the default will be to update the
        entire display from (0, 0) to (239, 319)
        '''
        self._command(0x2A); self._data([x1 >> 8, x1, x2 >> 8, x2])
        self._command(0x2B); self._data([y1 >> 8, y1, y2 >> 8, y2])
        self._command(0x2C)  # write to RAM

    def flush(self, x1, y1, x2, y2):
        '''write data in framebuffer to screen'''
        with self._lock:
            self._set_window(x1, y1, x2, y2)
            self._data(self.fb[y1:y2+1, x1:x2+1].flatten().tolist())

    def reset(self):
        if self._rst is None:
            return False
        self._rst.value = 1
        time.sleep(0.02)
        self._rst.value = 0
        time.sleep(0.02)
        self._rst.value = 1
        time.sleep(0.15)
        return True

    def start(self, *a, **k):
        '''
        Initialize the display. This should be called at least once before
        using other draw_* methods.
        '''
        assert self._opened, 'you need to open a spi device first'
        if self.reset():
            time.sleep(0.5)
        self._command(0xEF); self._data([0x03, 0x80, 0x02])
        self._command(0xCF); self._data([0x00, 0xC1, 0x30])
        self._command(0xED); self._data([0x64, 0x03, 0x12, 0x81])
        self._command(0xE8); self._data([0x85, 0x00, 0x78])
        self._command(0xCB); self._data([0x39, 0x2C, 0x00, 0x34, 0x02])
        self._command(0xF7); self._data([0x20])
        self._command(0xEA); self._data([0x00, 0x00])
        self._command(0xC0); self._data([0x23])
        self._command(0xC1); self._data([0x10])
        self._command(0xC5); self._data([0x3e, 0x28])
        self._command(0xC7); self._data([0x86])
        self._command(0x36); self._data([0x58])
        self._command(0x3A); self._data([0x55])
        self._command(0xB1); self._data([0x00, 0x18])
        self._command(0xB6); self._data([0x08, 0x82, 0x27])
        self._command(0xF2); self._data([0x00])
        self._command(0x26); self._data([0x01])
        self._command(0xE0); self._data([0x0F, 0x31, 0x2B, 0x0C, 0x0E,
                                         0x08, 0x4E, 0xF1, 0x37, 0x07,
                                         0x10, 0x03, 0x0E, 0x09, 0x00])
        self._command(0xE1); self._data([0x00, 0x0E, 0x14, 0x03, 0x11,
                                         0x07, 0x31, 0xC1, 0x48, 0x08,
                                         0x0F, 0x0C, 0x31, 0x36, 0x0F])
        self._command(0x11)   # Exit Sleep
        time.sleep(0.12)
        self._command(0x29)   # Display on
        time.sleep(0.2)
        self.set_rotation(3)  # Set screen direction
        self.clear()

    def close(self, *a, **k):
        if not self._opened:
            return
        self.clear()
        super(ILI9341_API, self).close()

        self._dc.value = 0
        self._dc.export = False
        if self._rst is not None:
            self._rst.value = 0
            self._rst.export = False
        self._opened = False

    def draw_point(self, x, y, c, *a, **k):
        self.fb[y, x] = c
        self.flush(x, y, x, y)

    def draw_line(self, x1, y1, x2, y2, c, *a, **k):
        # draw vertical or horizontal line
        if (x1 == x2) or (y1 == y2):
            self.draw_rectf(x1, y1, x2, y2, c)
            return
        # draw a line cross point(x1, y1) and point(x2, y2)
        # 1. get line function `y = k * x + b`
        k, b = np.polyfit([x1, x2], [y1, y2], 1)
        if abs(y2 - y1) > abs(x2 - x1):
            # 2. use y as index to get smoother line
            _y = np.arange(min(y1, y2), max(y1, y2)).astype(np.uint16)
            _x = np.round((_y - b) / k).astype(np.uint16)
        else:
            # 2. use x as index to get smoother line
            _x = np.arange(min(x1, x2), max(x1, x2)).astype(np.uint16)
            _y = np.round(k * _x + b).astype(np.uint16)
        # 3. plot _x, _y on framebuffer
        self.fb[_y, _x] = c
        self.flush(_x.min(), _y.min(), _x.max(), _y.max())

    def draw_rect(self, x1, y1, x2, y2, c, *a, **k):
        self.fb[y1, x1:x2] = self.fb[y2, (x1 + 1):(x2 + 1)] = c
        self.fb[y1:y2, x2] = self.fb[(y1 + 1):(y2 + 1), x1] = c
        if max((x2 - x1), (y2 - y1)) < 45:  # 45*45*2 = 4050 bytes < 4096 chunk
            self.flush(x1, y1, x2, y2)      # draw whole rectangle
        else:
            self.flush(x1, y1, x2 - 1, y1)  # draw top line
            self.flush(x1 + 1, y2, x2, y2)  # draw bottom line
            self.flush(x1, y1 + 1, x1, y2)  # draw left line
            self.flush(x2, y1, x2, y2 - 1)  # draw right line

    def draw_rectf(self, x1, y1, x2, y2, c, *a, **k):
        self.fb[y1:(y2 + 1), x1:(x2 + 1)] = c
        self.flush(x1, y1, x2, y2)

    def draw_circle(self, x, y, r, c, s=0, e=360, step=0.5, f=False, *a, **k):
        '''
        x, y: center of circle
        r: radius
        c: color
        s, e: start and end degree between [0, 360], default s=0, e=360
        step: this value smaller, the smooth level of arc higher
        f: whether fill circle with color, only support s=0, 90, 180, 270
            and e=90, 180, 270, 360
        '''
        d = np.arange(s, e, step) * np.pi / 180        # degree to rad
        _x, _y = x + r * np.cos(d), y - r * np.sin(d)  # rad to pos (float)
        _x, _y = np.round([_x, _y]).astype(np.uint32)  # pos to index (int)
        d = np.unique(_x << 16 | _y)                   # remove repeat index
        _x, _y = d >> 16, d & 0xffff                   # recover index data
        if f is True:
            if s in [90, 180]:                         # fill from _x to x
                for _x, _y in np.stack([_x, _y], -1):
                    self.fb[_y, _x:x] = c
            elif s in [0, 270]:                        # fill from x to _x
                for _x, _y in np.stack([_x, _y], -1):
                    self.fb[_y, x:_x] = c
            else:
                raise ValueError('only support s=0, 90, 180, 270')
        else:
            self.fb[_y, _x] = c
        self.flush(_x.min(), _y.min(), _x.max(), _y.max())

    def draw_circlef(self, x, y, r, c, *a, **k):
        '''
        draw a filled whole circle, faster than draw_circle(s=0, e=360, f=True)
        '''
        _y = np.arange(y - r, y + r + 1).astype(np.uint16)
        _x = np.round(np.sqrt(r**2 - (_y - y)**2)).astype(np.uint16)
        for m_x, m_y in np.stack([_x, _y], -1):
            self.fb[m_y, (x - m_x):(x + m_x)] = c
        self.flush(x - r, y - r, x + r, y + r)

    def draw_round(self, x, y, r, c, m, *a, **k):
        '''
        x, y: center of round corner
        r: radius
        c: color, 2-bytes list of rgb565, such as `blue`: [0x00, 0x1F]
        m: corner num, see below graph, m = 0, 1, 2, 3
        +--------------------------------+
        |(0, 0)                          |
        |                                |
        |        m=1       m=0           |
        |         +---------+            |
        |         |I am rect|            |
        |         +---------+            |
        |        m=2       m=3           |
        |                                |
        |                      (319, 239)|
        +--------------------------------+
        '''
        assert m in [0, 1, 2, 3], 'Invalid corner number!'
        self.draw_circle(x, y, r, c, m * 90, (m + 1) * 90)

    def draw_roundf(self, x, y, r, c, m, step=0.5, *a, **k):
        '''
        See Also
        --------
        draw_round
        draw_circle
        '''
        assert m in [0, 1, 2, 3], 'Invalid corner number!'
        self.draw_circle(x, y, r, c, m * 90, (m + 1) * 90, f=True)

    def draw_round_rect(self, x1, y1, x2, y2, r, c, *a, **k):
        self.draw_round(x2 - r, y2 - r, r, c, 0)  # right - bottom
        self.draw_round(x1 + r, y2 - r, r, c, 1)  # left  - bottom
        self.draw_round(x1 + r, y1 + r, r, c, 2)  # left  - top
        self.draw_round(x2 - r, y1 + r, r, c, 3)  # right - top
        self.draw_rectf(x1 + r, y1, x2 - r, y1, c)
        self.draw_rectf(x1 + r, y2, x2 - r, y2, c)
        self.draw_rectf(x1, y1 + r, x1, y2 - r, c)
        self.draw_rectf(x2, y1 + r, x2, y2 - r, c)

    def draw_round_rectf(self, x1, y1, x2, y2, r, c, *a, **k):
        self.draw_roundf(x2 - r, y2 - r, r, c, 0)
        self.draw_roundf(x1 + r, y2 - r, r, c, 1)
        self.draw_roundf(x1 + r, y1 + r, r, c, 2)
        self.draw_roundf(x2 - r, y1 + r, r, c, 3)
        self.draw_rectf(x1 + r, y1, x2 - r, y2, c)
        self.draw_rectf(x1, y1 + r, x1 + r, y2 - r, c)
        self.draw_rectf(x2 - r, y1 + r, x2, y2 - r, c)

    def draw_img(self, x, y, img, *a, **k):
        '''draw RGB[A] img with shape of (height, width, depth) at (x, y)'''
        img = np.atleast_3d(img).astype(np.uint8)
        x1, y1 = x, y
        x2 = max(min(x1 + img.shape[1], self.width), x1)
        y2 = max(min(y1 + img.shape[0], self.height), y1)
        # img shape correction and extracting alpha channel
        img = img[:(y2 - y1), :(x2 - x1)].astype(np.int16)
        if img.shape[2] == 4:
            img, alpha = np.split(img, [-1], axis=-1)
            alpha = alpha.astype(np.float) / 255
        else:
            if img.shape[2] != 3:
                img = np.repeat(img[:, :, 0], 3, axis=-1)
            alpha = np.ones((y2 - y1, x2 - x1, 1), np.float)

        # calculate difference of image and current framebuffer
        current = np.split(self.fb[y1:y2, x1:x2].astype(np.uint16), 2, -1)
        current = np.int16(np.concatenate(rgb565to888_pro(*current), -1))
        # weight it with alpha channel
        dest = current + (img - current) * alpha
        # convert to rgb565 and draw back on framebuffer
        dest = np.split(dest.astype(np.uint16), 3, -1)
        dest = np.concatenate(rgb888to565_pro(*dest), -1).astype(np.uint8)
        self.fb[y1:y2, x1:x2] = dest
        self.flush(x1, y1, x2 - 1, y2 - 1)

    def draw_text(self, x, y, s, c, size=None, font=None, *a, **k):
        if font is not None and os.path.exists(font):
            self.setfont(font)
        if size is not None and self.size != size:
            self.setsize(size)
        assert self.font, '[ILI9341 API] font not set yet!'
        w, h = self.font.getsize(s)
        img = Image.new(mode='RGBA', size=(w, h))
        ImageDraw.Draw(img).text((0, 0), s, rgb565to888(*c), font)
        img = img.resize((w // 2, h // 2), resample=Image.ANTIALIAS)
        self.draw_img(x, y, np.array(img, dtype=np.uint8))

    def set_rotation(self, m):
        with self._lock:
            self._command(0x36)
            if (m % 4) == 0:
                self._data([ILI9341_MADCTL_MX | ILI9341_MADCTL_BGR])
            elif (m % 4) == 1:
                self._data([ILI9341_MADCTL_MV | ILI9341_MADCTL_BGR])
            elif (m % 4) == 2:
                self._data([ILI9341_MADCTL_MY | ILI9341_MADCTL_BGR])
            elif (m % 4) == 3:
                self._data([ILI9341_MADCTL_MX | ILI9341_MADCTL_MY |
                            ILI9341_MADCTL_MV | ILI9341_MADCTL_BGR])

    def clear(self, c=ILI9341_BLACK, *a, **k):
        self.draw_rectf(0, 0, self.width - 1, self.height - 1, c)


# THE END
