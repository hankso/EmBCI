#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/recorder/server.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-10-19 18:46:12

'''`embci.apps.recorder.Recorder` management WebUI.'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import sys

# requirements.txt: necessary: six
# requirements.txt: network: bottle
from six import string_types
import bottle

from embci.utils import find_task_by_name, find_tasks_by_class, null_func

from .base import globalvars, Recorder

__basedir__ = os.path.dirname(os.path.abspath(__file__))
rec_app = bottle.Bottle()


def rec_init():
    global rec_init
    rec_init = null_func
    if len(find_tasks_by_class(Recorder)) > 0:
        return
    from embci.io import LSLReader
    reader = globalvars.reader = LSLReader()
    try:
        reader.start()
    except RuntimeError:
        pass
    else:
        recorder = globalvars.recorder = Recorder(reader)
        recorder.start()


@rec_app.route('/')
def rec_manager():
    rec_init()
    bottle.redirect('manager.html')


@rec_app.route('/list')
def rec_list():
    lst = [
        {'id': i, 'name': rec.name, 'info': rec_info(rec)}
        for i, rec in enumerate(find_tasks_by_class(Recorder))
    ]
    return {
        'session': '<%s 0x%x>' % (repr(Recorder).strip('<>'), id(Recorder)),
        'pid': os.getpid(), 'server': repr(rec_app),
        'command': ' '.join(sys.argv), 'recorders': lst
    }


@rec_app.route('/info/<name>')
def rec_info(name):
    rec = rec_resolve_recorder(name)
    info = filter(lambda tup: not callable(tup[1]), rec._help_attrs)
    return dict(info)


def rec_resolve_recorder(name):
    if isinstance(name, string_types):
        rec = find_task_by_name(name, Recorder)
    else:
        rec = name
    if not isinstance(rec, Recorder):
        bottle.abort(400, 'Invalid recorder/name: `%s` > `%s`' % (name, rec))
    return rec


@rec_app.route('/command/<name>')
def rec_command_k(name, **kwargs):
    '''
    >>> rec_command_k('recorder_1', chunk=1)
    >>> rec_command_k(Recorder(), username='jackson', **{'event_merge': True})
    '''
    return rec_resolve_recorder(name).cmd(**kwargs or bottle.request.query)


@rec_app.route('/command/<name>/<cmd>')
def rec_command_a(name, cmd, *args):
    '''
    >>> rec_command_a('Rec_foo', 'summary', 'usage', 'help')
    >>> rec_command_a(Recorder(), 'start')
    '''
    return rec_resolve_recorder(name).cmd(*set(args).union([cmd]))


@rec_app.route('/srv/<filename:path>')
def rec_static_hook(filename):
    return bottle.HTTPError(404, 'File does not exist.')


@rec_app.route('/<filename:path>')
def rec_static_files(filename):
    if os.path.exists(os.path.join(__basedir__, filename)):
        return bottle.static_file(filename, __basedir__)
    bottle.redirect('/srv/' + filename)


application = rec_app
__all__ = ('application', )
