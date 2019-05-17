#!/usr/bin/env python
# coding=utf-8
#
# File: DBS/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 05 Mar 2019 02:07:51 CST

import sys

if __name__ == '__main__' and 'build' in sys.argv:
    # use `python -m embci.apps.DBS build` to update (rebuild) libdbs.so
    import os
    import shutil
    import tempfile
    import subprocess
    from .globalvars import __dir__
    from .utils import libfile, libpath
    basedir = os.path.join(__dir__, 'utils')
    source = os.path.join(basedir, 'libdbs.pyx')
    result = os.path.join(basedir, 'libdbs.c')
    target = os.path.splitext(libfile)[0]

    # =========================================================================
    # `python setup.py build_ext --build-lib tmpdir --build-temp tmpdir`
    #
    from Cython.Build import cythonize
    from distutils.extension import Extension
    from distutils.core import setup
    tmpd = tempfile.mkdtemp(dir=basedir)
    setup(
        script_args=['build_ext', '-f', '-b', tmpd, '-t', tmpd],  # gcc compile
        ext_modules=cythonize([
            Extension(target, [source]),  # cythonize
        ])
    )
    for fn in os.listdir(tmpd):
        if fn.startswith(target):
            shutil.move(os.path.join(tmpd, fn), libpath)
            print('`{}` has been updated!'.format(libpath))
    try:
        os.remove(result)
        shutil.rmtree(tmpd)
        subprocess.check_output(['strip', libpath])
    except Exception:
        pass
    sys.exit(0)


import bottle
from embci.webui import GeventWebsocketServer
from . import application, logger


def main():
    #  import logging
    #  import gevent.pywsgi
    #  from embci.utils import LoggerStream
    #  from geventwebsocket.handler import WebSocketHandler
    #  server = gevent.pywsgi.WSGIServer(
    #      listener=('0.0.0.0', 80), application=dbs,
    #      log=LoggerStream(logger, logging.DEBUG),
    #      error_log=LoggerStream(logger, logging.ERROR),
    #      handler_class=WebSocketHandler)
    #  server.serve_forever()
    bottle.run(application, host='0.0.0.0', port=8080,
               server=GeventWebsocketServer, logger=logger)


if __name__ == '__main__':
    sys.exit(main())
