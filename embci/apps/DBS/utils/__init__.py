#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/utils/__init__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 04 Mar 2019 17:06:43 CST

'''This file provides some key functions used in DBS.'''

#  magic marks for `EmBCI/tools/genrequire.py`
# requirements.txt: optional: reportlab
# requirements.txt: data-processing: scipy, numpy

# =============================================================================
# Load obfuscated code (Deprecated in v0.1.4)
#
#  import re, marshal, sys
#  with open(re.sub('.py[cod]?$', '.bin', __file__)) as f:
#      code = marshal.load(f)
#  try:
#      exec(code)
#  except Exception:
#      sys.exit()


# =============================================================================
# Protect source code with `Cython` and `gcc compiler` (Added in v0.1.5).
# More details at Cython homepage (http://cython.org/).
# Filename of dynamic link library will be like:
#     libdbs_<bitness>_<py_version>_<machine>.<suffix>
#
import os
import sys
import platform
import importlib

__dir__ = os.path.dirname(os.path.abspath(__file__))
__module__ = sys.modules[__name__]  # reference to current module
__target__ = [
    'generate_pdf', 'calc_coef',
    'process_register', 'process_realtime', 'process_fullarray'
]

libfile = 'libdbs_{pyversion}_{machine}.{suffix}'.format(
    #  bitness = 64 if sys.maxsize > 2 ** 32 else 32,
    pyversion = '%d%d' % (sys.version_info.major, sys.version_info.minor),
    machine = platform.machine() or 'x86_64',
    suffix = {
        'Linux': 'so',
        'Darwin': 'dylib',
        'Windows': 'dll',
        'Microsoft': 'dll',
    }.get(platform.system(), 'so')
)

libpath = os.path.join(__dir__, libfile)
sys.stderr.write('Using library file `{}`\n'.format(libpath))

libname = __name__ + '.' + os.path.splitext(libfile)[0]

try:
    mod = importlib.import_module(libname)
    for attr in __target__:
        if not hasattr(mod, attr):
            raise ImportError('No target named: ' + attr)
        setattr(__module__, attr, getattr(mod, attr))
except ImportError as e:
    sys.stderr.write(
        'Import failed, all functions will be masked as `None`\n%s\n' % str(e)
    )
    for attr in __target__:
        setattr(__module__, attr, None)
except Exception as e:
    sys.exit(str(e))

# THE END
