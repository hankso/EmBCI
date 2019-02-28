#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/tests/conftest.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Tue 26 Feb 2019 16:36:54 CST

'''Define some fixtures here.'''

import os
import subprocess

import pytest
import numpy as np

from embci.configs import DATADIR


@pytest.fixture(scope='session')
def username():
    return 'testing'


@pytest.fixture(scope='module')
def random_data():
    np.random.seed()
    return np.random.randn(1, 8, 1000)


@pytest.fixture
def clean_user_dir(username):
    userdir = os.path.join(DATADIR, username)
    if os.path.exists(userdir):
        subprocess.call(['rm', '-rf', userdir])
