#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/example/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-09-18 01:55:03

import os
import time

from bottle import request, response, redirect, run, template, Bottle
example = Bottle()

__basedir__ = os.path.dirname(os.path.abspath(__file__))
__index__ = os.path.join(__basedir__, 'index.html')


@example.route('/')
def index():
    # If user request https://HOST:PORT/apps/example, redirect to index.html
    redirect('index.html')


@example.route('/index.html')
def hello():
    last_time = request.get_cookie('time')
    response.set_cookie(
        'time', time.strftime('%a,%b %d %H:%M:%S %Y', time.localtime()))
    msg = ['I am NOT dead~']
    if last_time:
        msg.append('Welcome back, last visited at {}'.format(last_time))
    # use absolute filename instead of relative one
    return template(__index__, messages=msg)


def main():
    '''
    Now you can configure in setup.py like follows::

        extry_points = {
            'console_scripts': [
                'embci-apps-example = embci.apps.example:main',
            ]
        }

    And after ``python setup.py install``, you can simply call
    ``embci-apps-example`` in your terminal to run this example app.
    '''
    run(example, host='0.0.0.0', port=8080)


# provide an object named `application` for Apache + mod_wsgi and embci.webui
application = example
__all__ = ['application']
