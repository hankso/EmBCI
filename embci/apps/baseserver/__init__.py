#!/usr/bin/env python3
# coding=utf-8
#
# File: apps/baseserver/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-14 16:17:15

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os

# requirements.txt: network: bottle
import bottle

from embci.configs import DIR_DATA
from embci.utils import get_boolean
from embci.io import find_data_info

__basedir__ = os.path.dirname(os.path.abspath(__file__))
application = bottle.Bottle()


@application.route('/')
def base_root():
    bottle.redirect('index.html')


@application.route('/datafiles')
def base_datafile_list():
    if not os.path.exists(DIR_DATA):
        return {}
    users = [n for n in os.listdir(DIR_DATA) if not n.startswith(('.', '_'))]
    datalist = []
    for user in users:
        datalist.extend([{
            'username': user, 'filename': os.path.basename(fn),
            'link': 'datafiles/%s/%s' % (user, os.path.basename(fn)),
            'stat': base_datafile_info(fn)
        } for fns in find_data_info(user)[1].values() for fn in fns])
    for idx in range(len(datalist)):
        datalist[idx]['id'] = idx
    return {'users': users, 'datalist': datalist}


@application.get('/datafiles/<filename:path>')
def base_datafile_info(filename):
    path = os.path.join(DIR_DATA, filename)
    if not os.path.exists(path):
        bottle.abort(400, 'Data file not exists: `%s`' % filename)
    if get_boolean(bottle.request.query.get('download', 'False')):
        dirname, basename = os.path.split(path)
        return bottle.static_file(basename, dirname, download=True)
    stat = os.stat(path)
    return {name: getattr(stat, name) for name in [
        'st_mode', 'st_ino', 'st_dev', 'st_nlink',
        'st_uid', 'st_gid', 'st_size', 'st_atime', 'st_mtime', 'st_ctime'
    ]}


@application.delete('/datafiles/<filename:path>')
def base_datafile_delete(filename):
    try:
        os.remove(os.path.join(DIR_DATA, filename))
    except Exception:
        bottle.abort(400, 'Data file not exists: `%s`' % filename)


@application.route('/<filename:path>')
def base_static(filename):
    if os.path.exists(os.path.join(__basedir__, filename)):
        return bottle.static_file(filename, __basedir__)
    bottle.redirect('/srv/' + filename)


APPNAME = 'File Manager'
__all__ = ('application', )
