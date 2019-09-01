#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/setup.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-08-30 09:48:18

from setuptools import setup
import os
import sys
import glob
import platform

__basedir__ = os.path.dirname(os.path.abspath(__file__))
if __basedir__ not in sys.path:
    sys.path.insert(0, __basedir__)

import embci


def extract_requirements(fn):
    if not os.path.isfile(fn):
        return []
    with open(fn, 'r') as f:
        return [
            _.strip() for _ in f.readlines()
            if not _.startswith('#') and len(_.strip())
        ]


reqmods = extract_requirements(os.path.join(__basedir__, 'requirements.txt'))
devmods = list(set(
    extract_requirements(os.path.join(__basedir__, 'requirements-dev.txt'))
).difference(reqmods))


extras = dict(
    install_requires=reqmods,
    project_urls={
        'Documentation': 'https://embci.readthedocs.io/en/latest',
        'Gitbooks': 'https://embci.gitbook.io/doc/',
        'Funding': embci.__url__ + '#Funding',
        'Source Code': embci.__url__,
        'Bug Tracker': os.path.join(embci.__url__, 'issues')
    },
    entry_points={
        'console_scripts': [
            'embci-webui = embci.webui:main',
        ]
    },
    package_data={},
)

if platform.machine() in ['arm', 'aarch64']:
    extras['data_files'] = [
        (os.path.expanduser('~/.embci/'), ['files/service/embci.conf']),
        ('/etc/embci', glob.glob('files/service/*')),
        ('/etc/init.d/', ['files/service/embci']),
    ]

    def enable_autostart():
        import subprocess
        try:
            subprocess.call(['update-rc.d', 'embci', 'enable'])
        except OSError:
            print('No command `update-rc.d`?')
        except subprocess.CalledProcessError:
            print('Enable service `embci` failed.\nYou may want to manually'
                  'enable it with command `update-rc.d embci enable`')
    # EmBCI linux service is still developing
    #  import atexit
    #  atexit.register(enable_autostart)


setup(
    name         = embci.__title__,
    version      = embci.__version__,
    url          = embci.__url__,
    author       = embci.__author__,
    author_email = embci.__email__,
    license      = embci.__license__,
    description  = embci.__doc__,
    keywords     = embci.__keywords__,
    **extras
)
