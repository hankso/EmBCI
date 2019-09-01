#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/example/__main__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-05 13:44:56

'''
Example file __main__.py of single applications.
'''

import sys

import bottle

# Your need to provide an `application` object in __init__.py
from . import application  # this is exactly what embci.webui subapps loader do


def main():
    '''
    Parameter `reloader` is useful for debugging. It can automatically reload
    your app when the source code has been modified.

    But with bottle's auto-reloader taken care of your app, attribute
    ``__main__.__package__`` will be set to `None`. Because it is
    ``__package__`` that determines how to import, when you run with command
    :code:`python -m MyApp`, python will raise::

        from . import application
        ValueError: Attempted relative import in non-package.

    And if you don't run app with command :code:`python -m MyApp`, there's no
    reason this ``__main__.py`` should exist anymore. For more detail, see
    `this page <https://stackoverflow.com/questions/21233229>`_.
    '''
    # this is what embci.webui subapps runner actually do
    bottle.run(application, host='0.0.0.0', port=8080,)  # reloader=True)


if __name__ == '__main__':
    sys.exit(main())
