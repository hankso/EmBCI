#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/io/base.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-03-16 19:37:41

'''Save and Load Utilities'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import re
import time
import traceback

# requirements.txt: data: numpy, scipy, mne
import numpy as np
import scipy.io
import mne

from ..utils import mkuserdir, check_input, validate_filename, TempStream
from ..configs import DIR_DATA
from . import logger

__all__ = [
    'create_data_dict', 'get_label_dict',
    'save_data', 'load_data', 'load_label_data',
    'save_action',
]


@mkuserdir
def get_label_dict(username):
    '''
    Count all saved data files under user's directory that match a pattern:
    ${DIR_DATA}/${username}/${label}-${num}.${suffix}

    Returns
    -------
    out : tuple
        label_dict and summary string

    Examples
    --------
    >>> get_label_dict('test')
    ({
         'left': 16,
         'right': 21,
         'thumb_cross': 10,
    }, 'There are 3 actions with 47 records.\\n')
    '''
    label_dict = {}
    name_dict = {}
    for filename in sorted(os.listdir(os.path.join(DIR_DATA, username))):
        fn, ext = os.path.splitext(filename)
        if ext == '.gz':
            fn, ext = os.path.splitext(fn)
        if ext not in ['.mat', '.fif', '.csv'] or '-' not in fn:
            continue
        label, num = fn.split('-')
        if label in label_dict:
            label_dict[label] += 1
            name_dict[label].append(filename)
        else:
            label_dict[label] = 1
            name_dict[label] = [filename]

    # construct a neat summary report
    summary = 'There are {} actions with {} data recorded.'.format(
        len(label_dict), sum(label_dict.values()))
    if label_dict:
        maxname = max(len(fn) for fns in name_dict.values() for fn in fns) - 2
        summary += '\n  * ' + '\n  * '.join([
            label.ljust(maxname) + '%2d' % label_dict[label] +
            '\n    ' + '\n    '.join(name_dict[label])
            for label in label_dict])
    return label_dict, summary


def create_data_dict(data, label='default', sample_rate=500, suffix=None):
    '''
    Create a data_dict that can be saved by function `save_data`.

    Parameters
    ----------
    data : ndarray | array list | instance of mne.Raw[Array]
        2d or 3d array with a shape of [n_sample x ]num_channel x window_size
    label : str
        Action name, data label. Char '-' is not suggested in label.
    sample_rate : int
        Sample rate of data, default set to 500Hz.
    suffix : str
        Currently supported formats are MATLAB-style '.mat'(default),
        MNE-style '.fif[.gz]' and raw text '.csv'.

    Returns
    -------
    data_dict : dict
        {'data': array, 'label': str, 'sample_rate': int, ...}
    '''
    data_dict = {
        'label': str(label),
        'sample_rate': int(sample_rate)
    }
    if suffix is not None:
        data_dict['suffix'] = str(suffix)

    if isinstance(data, mne.io.BaseRaw):
        data_dict['info'] = data.info
        data_dict['sample_rate'] = data.info['sfreq']
        # 1 x num_channel x window_size
        data = data.get_data()[np.newaxis, :, :]
    elif data.ndim == 1:
        # 1 x 1 x window_size
        data = data[np.newaxis, np.newaxis, :]
    elif data.ndim == 2:
        # 1 x num_channel x window_size
        data = data[np.newaxis]
    elif data.ndim > 3:
        raise ValueError('data array with too many dimensions')

    data_dict['data'] = data
    return data_dict


@mkuserdir
def save_data(username, data_dict, suffix='mat', summary=False):
    '''
    Save data into ${DIR_DATA}/${username}/${label}-${num}.${suffix}

    Parameters
    ----------
    username : str
    data_dict : dict
        created by function create_data_dict(data, label, format, sample_rate)
    suffix : str
        Currently supported formats are MATLAB-style '.mat'(default),
        MNE-style '.fif[.gz]' and raw text '.csv'. Format setting in
        data_dict will overwrite this argument.
    summary : bool
        Whether to print summary of currently saved data, default `False`.

    Examples
    --------
    >>> data = np.random.rand(8, 1000) # 8chs x 4sec x 250Hz data
    >>> save_data('test', create_data_dict(data, 'random_data', 250))
    (8, 1000) data saved to ${DIR_DATA}/test/random_data-1.mat

    >>> raw = mne.io.RawArray(data, mne.create_info(8, 250))
    >>> save_data('test', create_data_dict(raw, format='fif.gz'))
    (8, 1000) data saved to ${DIR_DATA}/test/default-1.fif.gz
    '''
    try:
        label = data_dict['label']
        sample_rate = data_dict['sample_rate']
    except Exception:
        logger.warning(traceback.format_exc())
        raise TypeError('`data_dict` object created by function '
                        '`create_data_dict` is suggested.')

    # scan how many data files already there
    label_dict = get_label_dict(username)[0]
    num = label_dict.get(label, 0) + 1
    suffix = data_dict.pop('suffix', suffix)
    # function create_data_dict maybe offer mne.Info object
    info = data_dict.pop('info', None)
    if 'fif' in suffix and info is None:
        info = mne.create_info(data_dict['data'].shape[1], sample_rate)
    data = data_dict.pop('data', [])

    for sample in data:
        fn = os.path.join(
            DIR_DATA, username, '{}-{}.{}'.format(label, num, suffix))
        num += 1
        try:
            if suffix == 'mat':
                data_dict['data'] = sample
                scipy.io.savemat(fn, data_dict, do_compression=True)
            elif suffix == 'csv':
                np.savetxt(fn, sample, delimiter=',')
            elif suffix in ['fif', 'fif.gz']:
                # mute mne.io.BaseRaw.save info from stdout and stderr
                with TempStream(stdout=None, stderr=None):
                    mne.io.RawArray(sample, info).save(fn)
            else:
                logger.error('format `%s` is not supported.' % suffix)
                break
            logger.info('Save {} data to {}'.format(sample.shape, fn))
        except Exception:
            logger.warning('Save %s failed.' % fn)
            logger.warning(traceback.format_exc())
            if os.path.exists(fn):
                os.remove(fn)
            num -= 1

    if summary:
        print('\n' + get_label_dict(username)[1])


def load_label_data(username, label='default'):
    '''
    Load all data files that match ${DIR_DATA}/${username}/${label}-*.*

    Returns
    -------
    data_list : list
    '''
    data_list = []
    userdir = os.path.join(DIR_DATA, username)
    for fn in sorted(os.listdir(userdir)):
        if not fn.startswith(label):
            continue
        name, suffix = os.path.splitext(fn)
        if suffix == '.gz':
            name, suffix = os.path.splitext(name)
        fn = os.path.join(userdir, fn)
        try:
            if suffix == '.mat':
                data = scipy.io.loadmat(fn)['data']
                if data.ndim != 2:
                    raise IOError('data file {} not support'.format(fn))
            elif suffix == '.csv':
                data = np.loadtxt(fn, np.float32, delimiter=',')
            elif suffix == '.fif':
                with TempStream(stdout=None, stderr=None):
                    #  data = mne.io.RawFIF(fn).get_data()
                    data = mne.io.RawFIF(fn, preload=True)._data
            else:
                raise ValueError('format `%s` is not supported.' % suffix)
            data_list.append(data)
            logger.info('Load {} data from {}'.format(data.shape, fn))
        except Exception:
            logger.warning('Load {} failed.\n{}'.format(
                fn, traceback.format_exc()))
    return data_list


@mkuserdir
def load_data(username, pick=None, summary=True):
    '''
    Load all data files under directory ${DIR_DATA}/${username}

    Parameters
    ----------
    username : str
    pick : str | list or tuple of str | regex pattern | function
        load data files whose label name:
        equal to | inside | match | return True by appling `pick`
    summary : bool
        whether to print summary of currently saved data, default `False`.

    Returns
    -------
    out : tuple
        (data_array, label_list)
    data_array : ndarray
        3D array with a shape of n_samples x num_channel x window_size
    label_list : list
        String list with a length of n_samples. Each element indicate
        label(action name) of corresponding data sample.

    Examples
    --------
    >>> data, label = load_data('test')
    >>> len(data), label
    (5, ['default', 'default', 'default', 'right', 'left'])

    >>> _, _ = load_data('test', pick=('left', 'right'), summary=True)
    There are 3 actions with 5 data recorded.
      * default        3
        default-1.fif.gz
        default-2.fif.gz
        default-3.mat
      * right          1
        right-1.mat
      * left           1
        left-1.fif
    There are 2 actions with 2 data loaded.
      + left           1
      + right          1
    '''
    def filterer(label):
        if isinstance(pick, str):
            return label == pick
        if isinstance(pick, (tuple, list)):
            return label in pick
        if isinstance(pick, re._pattern_type):
            return bool(pick.match(label))
        if callable(pick):
            return pick(label)
        return True

    # pick labels that match the rule from label_dict
    label_dict, msg = get_label_dict(username)
    labels = list(filter(filterer, label_dict))

    data_list = []
    label_list = []
    for label in labels:
        data = load_label_data(username, label)
        data_list.extend(data)
        label_list.extend([label] * len(data))

    if summary:
        msg += '\nThere are {} actions with {} data loaded.'.format(
            len(labels), len(data_list))
        if len(data_list):
            maxname = max(len(s) for s in msg.split('\n')[1:-1]) - 6
            msg += '\n  + ' + '\n  + '.join([
                label.ljust(maxname) + '%2d' % label_list.count(label)
                for label in labels])
        print('\n' + msg.strip())

    # data_list: n_samples x (num_channel x window_size)
    # label_list: n_samples
    return data_list, label_list


def save_action(username, reader, action_list=['relax', 'grab']):
    '''
    Guidance on command line interface to save data with label to
    ${DIR_DATA}/${username}/${action}-*.mat

    Parameters
    ----------
    username : str
    reader : Reader
        Instance of `embci.io.readers.BaseReader`, repersenting a data stream.
    '''
    logger.info('You have to finish each action in {} seconds.'.format(
        reader.sample_time))
    num = check_input(('How many times would you like to record for each '
                       'action?(empty to abort): '), {}, times=999)
    if num == '' or not num.isdigit():
        return
    num = int(num)
    action_list = [
        action.replace('-', '_').replace(' ', ' ')
        for action in validate_filename(*action_list) if action
    ]
    name_list = action_list * num
    np.random.shuffle(name_list)
    while name_list:
        action = name_list.pop()
        print('action name: %s, start recording in 2s' % action)
        time.sleep(2)
        print('Start')
        time.sleep(reader.sample_time)
        print('Stop')
        save_data(username, summary=True, data_dict=create_data_dict(
            reader.data_frame, action, reader.sample_rate))
    return get_label_dict(username)[0]


# THE END
