#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/models/base.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-10 01:27:02

'''__doc__'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import math

# requirements.txt: machine-learning: keras
# Mute `Using X backend.` log.
# See #1406 @ https://github.com/keras-team/keras/issues/1406
from ..utils import TempStream
with TempStream(stderr=None):
    import keras                                                   # noqa: W611
from keras import Model
from keras.layers import Layer
from keras.utils.np_utils import to_categorical


class _Model(Model):
    pass


class _Layer(Layer):
    pass


class Models(object):
    def build(self, nb_classes, shape):
        self._preprocessers = []
        if self.model_type == 'Default':
            #  src: n_sample x n_channel x window_size
            #  out: n_sample x freq x time x n_channel
            #  label: n_sample x 1
            #  freq: int(1 + math.floor(float(nperseg)/2))
            #  time: int(1 + math.ceil(float(window_size)/(nperseg-noverlap)))
            self._preprocessers += [self._p.detrend]
            self._preprocessers += [self._p.notch]
            self._preprocessers += [self._p.stft]
            self._preprocessers += [lambda X: X.transpose(0, 2, 3, 1)]
            nperseg = int(self.fs / 5)
            noverlap = int(self.fs / 5 * 0.67)
            f = int(1 + math.floor(float(nperseg) / 2))
            t = int(1 + math.ceil(float(shape[2]) / (nperseg - noverlap)))
            self._Default(nb_classes, (f, t, shape[1]))
            self.epochs, self.batch_size = 60, 25

        elif self.model_type == 'CNN_LSTM':
            self._preprocessers += [self._p.detrend,
                                    self._p.notch,
                                    self._p.stft,
                                    lambda X: X.transpose(0, 2, 3, 1)]
            nperseg = int(self.fs / 5)
            noverlap = int(self.fs / 5 * 0.67)
            f = int(1 + math.floor(float(nperseg) / 2))
            t = int(1 + math.ceil(float(shape[2]) / (nperseg - noverlap)))
            self._CNN_LSTM(nb_classes, (f, t, shape[1]))
            self.epochs, self.batch_size = 60, 20

        elif self.model_type == 'Double_Dense':
            #  src: n_sample x n_channel x window_size
            #  out: n_sample x n_channel x window_size
            #  label: n_sample x 1
            self._preprocessers += [self._p.detrend, self._p.notch]
            self._Double_Dense(nb_classes, shape[1:])
            self.epochs, self.batch_size = 200, 15

        elif self.model_type == 'SVM':
            #  src: n_sample x n_channel x window_size
            #  out: n_sample x series(n_channel * freq * time)
            #  label:  n_sample x 1
            self._preprocessers += [self._p.detrend,
                                    self._p.notch,
                                    self._p.stft]
            self._preprocessers += [lambda X: X.reshape(X.shape[0], -1)]
            self._SVM()
        self.built = True

    def train(self, data, label):
        if not self.built:
            raise RuntimeError('you need to build the model first')

        # preprocessing
        for f in self._preprocessers:
            data = f(data)
        label = to_categorical(label)

        # train the model
        if self.model_type == 'SVM':
            self.model.fit(data, label)
        elif self.model_type in ['Default', 'CNN_LSTM', 'Double_Dense']:
            self.model.fit(data, label, validation_split=0.2, shuffle=True,
                           batch_size=self.batch_size, epochs=self.epochs)

    def predict(self, data):
        if not self.built:
            raise RuntimeError('you need to build the model first')

        # preprocessing
        for f in self._preprocessers:
            data = f(data)

        # predict value
        if self.model_type == 'SVM':
            tmp = self.model.predict_proba(data)
        elif self.model_type in ['Default', 'CNN_LSTM', 'Double_Dense']:
            # tmp = self.model.predict_classes(data, verbose=0)
            tmp = self.model.predict_proba(data, verbose=0)

        return tmp.argmax(), tmp.max()

# THE END
