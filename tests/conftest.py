# coding=utf-8
#
# File: EmBCI/tests/conftest.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-26 16:36:54

'''Define some fixtures here.'''

import os
import subprocess

import pytest
import numpy as np

from embci.configs import DIR_DATA


@pytest.fixture(scope='session')
def username():
    return 'testing'


@pytest.fixture(scope='module')
def random_data():
    np.random.seed()
    return np.random.randn(2, 8, 1024)


@pytest.fixture
def clean_userdir(username):
    def clean(userdir=os.path.join(DIR_DATA, username)):
        if os.path.exists(userdir):
            subprocess.call(['rm', '-rf', userdir])
    return clean
