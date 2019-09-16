#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/models/others.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-10 01:32:59

'''__doc__'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# requirements.txt: machine-learning: sklearn
from sklearn import svm


def SVM(self):
    return svm.SVC()
