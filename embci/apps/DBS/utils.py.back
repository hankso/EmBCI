#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/utils.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 04 Mar 2019 17:06:43 CST

'''
This file provides some key functions used in DBS from obfuscated source
codes at `utils.bin` in binary format.
'''

# built-in
import re
import sys
import marshal
import traceback

# requirements.txt: optional: reportlab
# requirements.txt: data-processing: scipy, numpy

# =============================================================================
# load obfuscated codes
#
with open(re.sub('.py[cod]?$', '.bin', __file__)) as f:
    code = marshal.load(f)
try:
    exec(code)
except Exception:
    traceback.print_exc()
    sys.exit()
