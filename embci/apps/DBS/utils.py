#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/utils.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 04 Mar 2019 17:06:43 CST

'''__doc__'''

# built-in
import os

# requirements.txt: optional: reportlab
try:
    from reportlab.pdfbase import ttfonts, pdfmetrics
    from reportlab.pdfgen import canvas
    _reportlib_ = True
except ImportError:
    _reportlib_ = False

from embci.configs import BASEDIR, DATADIR
from embci.utils import mkuserdir, time_stamp

DEFAULT_FONT = os.path.join(BASEDIR, 'files/fonts/yahei_mono.ttf')


@mkuserdir
def generate_pdf(username, **kwargs):
    if _reportlib_ is False:
        return {}
    # load font
    fontpath = kwargs.get('fontpath', DEFAULT_FONT)
    fontname = os.path.splitext(os.path.basename(fontpath))[0]
    if fontname not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(ttfonts.TTFont(fontname, fontpath))
    pdfpath = os.path.join(
        username, kwargs.get('filename', time_stamp() + '.pdf'))
    # plot on empty pdf
    c = canvas.Canvas(os.path.join(DATADIR, pdfpath), bottomup=0)
    c.setFont(fontname, 30)
    c.drawString(65, 80, u'天坛医院DBS术后调控肌电报告单')
    c.setFontSize(20)
    c.line(30, 120, 580, 120)
    str1 = (u'姓名: {username:^8s}  性别: {gender:>2s}  '
            u'年龄: {age:>3s}  病号ID: {id}')
    c.drawString(35, 150, str1.format(**kwargs))
    c.line(30, 165, 580, 165)
    c.line(30, 710, 580, 710)
    str2 = (u'改善率   震颤： {tr:4.1f}%    '
            u'僵直： {sr:4.1f}%    运动： {mr:4.1f}%')
    c.drawString(35, 740, str2.format(**kwargs))
    c.line(30, 755, 580, 755)
    c.drawImage(os.path.join(DATADIR, kwargs['img_pre']), 32, 190)
    c.drawImage(os.path.join(DATADIR, kwargs['img_post']), 32, 450)
    c.setFontSize(24)
    c.drawString(360, 250, u'术前')
    c.drawString(360, 510, u'术后')
    c.setFontSize(18)
    c.drawString(380, 290, u'震颤： {:7.4f}Hz'.format(kwargs['tb']))
    c.drawString(380, 320, u'僵直： {:7.4f}'.format(kwargs['sb']))
    c.drawString(380, 350, u'运动： {:7.4f}'.format(kwargs['mb']))
    c.drawString(380, 550, u'震颤： {:7.4f}Hz'.format(kwargs['ta']))
    c.drawString(380, 580, u'僵直： {:7.4f}'.format(kwargs['sa']))
    c.drawString(380, 610, u'运动： {:7.4f}'.format(kwargs['ma']))
    c.drawString(35, 795, u'医师签字：')
    c.setFontSize(15)
    c.drawString(450, 800, 'Powered by Cheitech')
    c.save()
    return {'pdfpath': pdfpath}
