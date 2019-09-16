#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/models/network.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-10 01:31:26

'''__doc__'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from keras import Sequential
from keras.layers import Dense, Dropout, Flatten, Conv2D
from keras.layers import MaxPooling2D, TimeDistributed, LSTM

from . import logger


def Default(self, nb_classes, input_shape):
    logger.info('Building 2 layers CNN model with data shape: {}'
                .format(input_shape))
    model = Sequential()
    model.add(Conv2D(
        filters=16,
        kernel_size=3,
        padding='valid',
        activation='relu',
        input_shape=input_shape))
    model.add(MaxPooling2D(3))
    model.add(Conv2D(
        filters=8,
        kernel_size=3,
        padding='valid',
        activation='relu'))
    model.add(MaxPooling2D(3))
    model.add(Flatten())
    model.add(Dense(128, activation='relu'))
    model.add(Dense(64, activation='relu'))
    model.add(Dense(nb_classes, activation='softmax'))
    model.compile(
        loss='categorical_crossentropy',
        optimizer='adadelta', metrics=['accuracy'])
    return model


def CNN_LSTM(self, nb_classes, input_shape):
    logger.info('Building 2 layers CNN 1 layer LSTM model with data shape: {}'
                .format(input_shape))
    model = Sequential()
    model.add(TimeDistributed(
        Conv2D(32, 5, 5, padding='same'),
        activation='relu',
        input_shape=input_shape))
    model.add(TimeDistributed(Conv2D(32, 5, 5), activation='relu'))
    model.add(TimeDistributed(MaxPooling2D(5)))
    model.add(TimeDistributed(Dropout(0.25)))
    model.add(TimeDistributed(Flatten()))
    model.add(LSTM(16, return_sequences=True))
    model.add(Dense(10, actication='relu'))
    model.add(Dense(nb_classes, activation='softmax'))
    model.compile(
        loss='categorical_crossentropy',
        optimizer='adadelta', metrics=['accuracy'])
    return model


def Double_Dense(self, nb_classes, input_shape):
    logger.info('Building 2 layers Dense model with data shape: {}'
                .format(input_shape))
    model = Sequential()
    model.add(Dense(128, activation='relu', input_shape=input_shape))
    model.add(Dense(72, activation='relu'))
    model.add(Flatten())
    model.add(Dense(nb_classes, activation='softmax'))
    model.compile(
        loss='categorical_crossentropy',
        optimizer='adadelta', metrics=['accuracy'])
    return model

# THE END
