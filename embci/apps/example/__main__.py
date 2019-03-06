#!/usr/bin/env python
# coding=utf-8
#
# File: apps/example/__main__.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 05 Mar 2019 13:44:56 CST

'''
Example file __main__.py of single applications.
'''

import sys

import bottle

# Your need to provide an `application` object in __init__.py
from . import application


def main():
    '''
    Parameter `reloader` is useful for debugging. It can automatically
    reload your app when the source code has been modified.

    But with bottle's auto-reloader takes care of your app, attribute
    `__main__.__package__` will be set to `None`, and then you can't run
    your app with command :code:`python -m MyApp`. There's also no reason
    that this __main__.py should exist anymore.

    When you run with command :code:`python -m MyApp`, python will raise::

        from . import application
        ValueError: Attempted relative import in non-package.

    Because `__package__` determines how to import. For more detail,
    see `this page <https://stackoverflow.com/questions/21233229>`_.
    '''
    bottle.run(application, host='0.0.0.0', port=8080,)  # reloader=True)


if __name__ == '__main__':
    sys.exit(main())
