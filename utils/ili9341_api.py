 #!/usr/bin/env python2
# -*- coding: utf-8 -*-
'''
Created on Wed May 23 02:16:40 2018
Modified ILI9341 python api based on Tony DiCola's Adafruit ILI9341 library
@author Tony DiCola  @author: hank
'''
# built-ins
import time

# pip install spidev, pillow, numpy
import spidev
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# from ./
from gpio4 import SysfsGPIO

# ILI9341 Pin mapping
PIN_DC              = 2
PIN_RST             = 3
# constants
WIDTH               = 320
HEIGHT              = 240
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
# colors
ILI9341_BLACK       = 0x0000
ILI9341_BLUE        = 0x001F
ILI9341_RED         = 0xF800
ILI9341_GREEN       = 0x07E0
ILI9341_CYAN        = 0x07FF
ILI9341_MAGENTA     = 0xF81F
ILI9341_YELLOW      = 0xFFE0
ILI9341_WHITE       = 0xFFFF
# rotation definition
ILI9341_MADCTL_MY   = 0x80
ILI9341_MADCTL_MX   = 0x40
ILI9341_MADCTL_MV   = 0x20
ILI9341_MADCTL_ML   = 0x10
ILI9341_MADCTL_RGB  = 0x00
ILI9341_MADCTL_BGR  = 0x08
ILI9341_MADCTL_MH   = 0x04


def color565(r, g, b):
    '''
    Convert red, green, blue components to a 16-bit 565 RGB value.
    Components should be values 0 to 255.
    '''
    c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return [c >> 8, c & 0xff]

def color_rgb(color):
    '''
    Convert 565 color format to rgb - return tuple
    '''
    r = (color >> 8) & 0xf8
    g = ((color >> 5) & 0x3f) << 2
    b = (color & 0x1f) << 3
    return (r, g, b)

class ILI9341_API:
    def __init__(self, dev, dc=PIN_DC, rst=PIN_RST, width=WIDTH, height=HEIGHT):
        '''
        Create an instance of the display using SPI communication.  Must
        provide the GPIO pin number for the D/C pin and the SPI driver.  Can
        optionally provide the GPIO pin number for the reset pin as the rst
        parameter.
        '''
        self._dc = SysfsGPIO(dc)
        self._dc.export = True
        self._dc.direction = 'out'
        self._rst = SysfsGPIO(rst)
        self._rst.export = True
        self._rst.direction = 'out'

        self._spi = spidev.SpiDev(dev[0], dev[1])
        self._spi.mode = 0
        self._spi.max_speed_hz = 25000000

        self.width = width
        self.height = height
        self.font = None
        self.size = 15

    def setfont(self, filename, size=None):
        if size is None:
            size = self.size
        self.font = ImageFont.truetype(filename, size * 2)
        self.size = size

    def setsize(self, size):
        if self.font is None:
            raise RuntimeError('[ILI9341 API] font not set')
        if self.size != size:
            self.font = ImageFont.truetype(self.font.path, size * 2)
            self.size = size

    def _command(self, data):
        '''
        Write an array of bytes to the display as command data.
        '''
        self._dc.value = 0
        self._spi.writebytes([data])

    def _data(self, data, chunk=4096):
        '''
        Write an array of bytes to the display as display data.
        '''
        self._dc.value = 1
        if len(data) < chunk:
            self._spi.writebytes(data)
        else:
            for start in range(0, len(data), chunk):
                self._spi.writebytes(data[start:min(start + chunk, len(data))])

    def reset(self):
        self._rst.value = 1
        time.sleep(0.02)
        self._rst.value = 0
        time.sleep(0.02)
        self._rst.value = 1
        time.sleep(0.15)

    def clear(self, *args, **kwargs):
        self.draw_rectf(0, 0, self.width - 1, self.height - 1, ILI9341_BLACK)

    def begin(self):
        '''
        Initialize the display.  Should be called once before other calls that
        interact with the display are called.
        '''
        self.reset()
        time.sleep(0.5)
        # Initialize the display.  Broken out as a separate function so it can
        # be overridden by other displays in the future.
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
        self._command(0x11)    # Exit Sleep
        time.sleep(0.12)
        self._command(0x29)    # Display on
        time.sleep(0.2)
        self.set_rotation(3)
        self.clear()

    def _set_window(self, x1=0, y1=0, x2=None, y2=None):
        '''
        Set the pixel address window for proceeding drawing commands. x1 and
        x2 should define the minimum and maximum x pixel bounds.  y1 and y2
        should define the minimum and maximum y pixel bound.  If no parameters
        are specified the default will be to update the entire display from 0,0
        to 239,319.
        '''
        if x2 is None:
            x2 = self.width-1
        if y2 is None:
            y2 = self.height-1
        self._command(0x2A); self._data([x1 >> 8, x1, x2 >> 8, x2])
        self._command(0x2B); self._data([y1 >> 8, y1, y2 >> 8, y2])
        self._command(0x2C)        # write to RAM

    def _fill(self, c, n):
        '''
        fill `n` continous pixels with color `c`
        '''
        self._data(color565(c >> 16, (c >> 8) & 0xff, c & 0xff) * n)

    def draw_point(self, x, y, c):
        self._set_window(x, y, x, y)
        self._fill(c, 1)

    def draw_line(self, x1, y1, x2, y2, c):
        # draw vertical or horizontal line
        if (x1 == x2) or (y1 == y2):
            self.draw_rectf(x1, y1, x2, y2, c)
        # draw a line cross point(x1, y1) and point(x2, y2)
        else:
            # get line `y = k * x + b`
            k, b = np.polyfit([x1, x2], [y1, y2], 1)
            if abs(y2 - y1) > abs(x2 - x1):
                # use y as index to get smoother line
                t = np.arange(min(y1, y2), max(y1, y2))
                t = np.round(np.stack([(t - b)/k, t], -1)).astype(np.int)
            else:
                # use x as index to get smoother line
                t = np.arange(min(x1, x2), max(x1, x2))
                t = np.round(np.stack([t, k*t + b], -1)).astype(np.int)
            for x, y in t:
                self.draw_point(x, y, c)

    def draw_rect(self, x1, y1, x2, y2, c):
        # draw top line
        self.draw_rectf(x1, y1, x2, y1, c)
        # draw bottom line
        self.draw_rectf(x1, y2, x2, y2, c)
        # draw left line
        self.draw_rectf(x1, y1, x1, y2, c)
        # draw right line
        self.draw_rectf(x2, y1, x2, y2, c)

    def draw_rectf(self, x1, y1, x2, y2, c):
        x1, y1, x2, y2 = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        self._set_window(x1, y1, x2, y2)
        self._fill(c, (x2 - x1 + 1) * (y2 - y1 + 1))

    def _draw_arc(self, x, y, r, c, s=0, e=360, step=1, f=False):
        '''
        x, y: center of arc
        r: radius
        c: color
        s: start degree, default 0
        e: end degree, default 360
        step: as step become higher, smooth level of arc grow
        f: fill or not, default False
        '''
        d = np.arange(s, e, step) * np.pi / 180
        d = np.round(r * np.stack([np.sin(d), np.cos(d)], -1))
        d = d.astype(np.int).tolist()
        if f:
            for i, p in enumerate(d):
                if p not in d[:i]:
                    self.draw_line(x, y, x + p[0], y + p[1], c)
        else:
            for i, p in enumerate(d):
                if p not in d[:i]:
                    self.draw_point(x + p[0], y + p[1], c)

    def draw_circle(self, x, y, r, c):
        if r > 50:
            self._draw_arc(x, y, r, c, f=True)
        else:
            self._draw_arc(x, y, r, c)

    def draw_circlef(self, x, y, r, c):
        '''
        do not use self._draw_arc(f=True) to draw circlef, it's too slow
        '''
        for _x in range(x - r, x + r + 1):
            _y = int(round((r**2 - (x - _x)**2)**0.5))
            self.draw_rectf(_x, y - _y, _x, y + _y, c)

    def draw_round(self, x, y, r, m, c):
        '''
        param `m` means corner num, see below graph
            0      1
             +----+
             |    |
             +----+
            2      3
        '''
        self._draw_arc(x, y, r, c, s=m*90, e=(m + 1)*90)

    def draw_roundf(self, x, y, r, m, c):
        self._draw_arc(x, y, r, c, s=m*90, e=(m + 1)*90, f=True)

    def draw_round_rect(self, x1, y1, x2, y2, r, c):
        x1, y1, x2, y2 = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        r = max(min((x2 - x1 + 1)/2, (y2 - y1 + 1)/2, r), 1)
        self.draw_round(x1 + r, y1 + r, r, 2, c)  #  left - top
        self.draw_round(x2 - r, y1 + r, r, 1, c)  # right - top
        self.draw_round(x1 + r, y2 - r, r, 3, c)  #  left - bottom
        self.draw_round(x2 - r, y2 - r, r, 0, c)  # right - bottom
        self.draw_rectf(x1 + r, y1, x2 - r, y1, c)
        self.draw_rectf(x1 + r, y2, x2 - r, y2, c)
        self.draw_rectf(x1, y1 + r, x1, y2 - r, c)
        self.draw_rectf(x2, y1 + r, x2, y2 - r, c)

    def draw_round_rectf(self, x1, y1, x2, y2, r, c):
        x1, y1, x2, y2 = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        r = max(min((x2 - x1 + 1)/2, (y2 - y1 + 1)/2, r), 1)
        self.draw_roundf(x1 + r, y1 + r, r, 2, c)
        self.draw_roundf(x2 - r, y1 + r, r, 1, c)
        self.draw_roundf(x1 + r, y2 - r, r, 3, c)
        self.draw_roundf(x2 - r, y2 - r, r, 0, c)
        self.draw_rectf(x1 + r, y1, x2 - r, y2, c)
        self.draw_rectf(x1, y1 + r, x1 + r, y2 - r, c)
        self.draw_rectf(x2 - r, y1 + r, x2, y2 - r, c)

    def draw_img(self, x, y, img):
        '''
        Draw the contents of buff on the screen
        '''
        x1, y1 = x, y
        x2 = max(min(x1 + img.shape[1], self.width - 1), x1)
        y2 = max(min(y1 + img.shape[0], self.height - 1), y1)
        # crop img to limited size and convert to two-bytes(5-6-5) color
        data = img[:y2-y1, :x2-x1].reshape(-1, 3).astype(np.uint16)
        data = np.stack(color565(data[:, 0], data[:, 1], data[:, 2]), axis=-1)
        self._set_window(x1, y1, x2 - 1, y2 - 1)
        self._data(data.reshape(-1).tolist())

    def draw_text(self, x, y, s, c, size=None):
        if size is not None and self.size != size:
            self.setsize(size)
        w, h = self.font.getsize(s)
        img = Image.new('RGB', (w, h))
        ImageDraw.Draw(img).text((0, 0), s, c, self.font)
        img = img.resize((w/2, h/2), resample=Image.ANTIALIAS)
        self.draw_img(x, y, np.array(img, dtype=np.uint8))

    def set_rotation(self, m):
        self._command(0x36)
        if (m % 4) == 0:
            self._data([ILI9341_MADCTL_MX | ILI9341_MADCTL_BGR])
        elif (m % 4) == 1:
            self._data([ILI9341_MADCTL_MV | ILI9341_MADCTL_BGR])
        elif (m % 4) == 2:
            self._data([ILI9341_MADCTL_MY | ILI9341_MADCTL_BGR])
        elif (m % 4) == 3:
            self._data([ILI9341_MADCTL_MX \
                        | ILI9341_MADCTL_MY \
                        | ILI9341_MADCTL_MV \
                        | ILI9341_MADCTL_BGR])

if __name__ == '__main__':
    ili = ILI9341_API((0, 1))
    ili.begin()
    ili.setfont('./yahei_mono.ttf')
    for i in range(240):
        ili.draw_point(i, i, int(i/240.0*0xffaa00))
    ili.draw_line(240, 0, 0, 240, 0xffffff)
    ili.draw_rect(10, 20, 20, 30, 0x00ff00)
    ili.draw_rectf(10, 35, 20, 45, 0x0000ff)
    ili.draw_circle(30, 50, 10, 0xaa00aa)
    ili.draw_circlef(30, 75, 14, 0x00aa00)
    ili.draw_round(100, 100, 15, 0, 0xff0000)
    ili.draw_round(100, 100, 15, 1, 0x00ff00)
    ili.draw_round(100, 100, 15, 2, 0x0000ff)
    ili.draw_round(100, 100, 15, 3, 0xaaffaa)
    ili.draw_round_rectf(150, 120, 300, 220, 7, 0x81d8d2) # tiffany blue
    ili.draw_text(200, 200, 'cheitech', np.random.randint(65535))
