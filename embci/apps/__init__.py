#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/apps/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-03 21:57:59

'''
This provide an app doc CLI interface by typing in `python -m embci.apps`.
'''

import os
__basedir__ = os.path.dirname(os.path.abspath(__file__))
del os


# TODO: load apps config file and mask them here.

__doc__ += '''
Subapps are actually modules. App with a value of `None` means it has been
`masked` (i.e. cannot use). Users can mask apps in two ways:
    1. let embci.apps.AppToBeMasked = None
    2. use command option `python -m embci.webui --exclude=AppNoUse`
'''
no_exist_app = None
system = None  # do not load app system by webui

__doc__ += '''
A subapp's default name is its folder's name. If a subapp has an attribute
`APPNAME`, its value will be displayed on webpage and app-list instead of the
folder name.
'''
from . import WiFi; WiFi.APPNAME = 'Network'                       # noqa: E702

__doc__ += '''
But you can also change subapp's name by renaming the module object and
specifing new name in `embci.apps.__all__`
'''
from . import example as Example

__doc__ += '''
If a subapp has an attribute `HIDDEN` (bool), it controls whether the app will
be display on webpage and app-list (embci.webui still can load it correctly).
'''
from . import auth; auth.HIDDEN = True                             # noqa: E702


__all__ = ['no_exist_app', 'WiFi', 'Example', 'auth']
