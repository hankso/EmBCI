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

# requirements.txt: data: numpy, scipy, mne==0.17
# requirements.txt: necessary: six
import numpy as np
import scipy.io
import mne
from six import string_types

from ..utils import (
    mkuserdir, check_input, typename, validate_filename,
    TempStream
)
from ..configs import DIR_DATA
from . import logger

__all__ = [
    'create_data_dict', 'find_data_info',
    'save_trials', 'save_chunks', 'save_action',
    'load_data', 'load_mat', 'load_label_data',
    'validate_datafile',
]


_name_datafile_pattern = re.compile(r'^([ \w\.-]+)-(\d+)\.(\w+)(?:\.gz)?$')
def find_data_info(username):                                      # noqa: W611
    '''
    Count all saved data files under user's directory that match a pattern:
    ${DIR_DATA}/${username}/${label}-${num}.${suffix}[.gz]

    Returns
    -------
    out : tuple
        label_dict, filename_dict and summary string

    Examples
    --------
    >>> find_data_info('test')
    ({
        'left': [0, 1, 2, 5, 8, 9, 10],
        'right': [2, 3, 4, 5],
        'thumb_cross': [1, 2, 3, 4, 5]
    }, {
        'left': ['/path/to/left-0.mat', '/path/to/left-1.fif', ...],
        'right': ['/path/to/right-2.h5', '/path/to/right-3', ...],
        'thumb_cross': [...]
    }, 'There are 3 actions with 16 records.\\n')
    '''
    label_dict = {}
    name_dict = {}
    root = os.path.join(DIR_DATA, username)
    if not os.path.exists(root):
        return label_dict, name_dict, ''
    for filename in sorted(os.listdir(root)):
        if not _name_datafile_pattern.match(filename):
            continue
        label, num, ext = _name_datafile_pattern.findall(filename)[0]
        if ext not in ['mat', 'fif', 'h5', 'csv']:
            continue
        num = int(num)
        if label in label_dict:
            label_dict[label].append(num)
            name_dict[label].append(filename)
        else:
            label_dict[label] = [num]
            name_dict[label] = [filename]
    # construct a neat summary report
    summary = 'There are {} actions with {} data recorded.'.format(
        len(label_dict), sum(map(len, label_dict.values())))
    if label_dict:
        maxname = max(len(fn) for fns in name_dict.values() for fn in fns) - 2
        summary += '\n  * ' + '\n  * '.join([
            label.ljust(maxname) + '%2d' % len(label_dict[label]) +
            '\n    ' + '\n    '.join(name_dict[label])
            for label in label_dict
        ])
    for label in name_dict:
        name_dict[label] = [os.path.join(root, fn) for fn in name_dict[label]]
    return label_dict, name_dict, summary


@mkuserdir
def validate_datafile(username, label='default', checkname=False):
    if checkname:
        username = ''.join([
            c for c in validate_filename(username) if c not in '()[]'
        ]).replace(' ', '_').replace('.', ' ')
    label = validate_filename(label)
    label_dict = find_data_info(username)[0]
    ns = label_dict.get(label, [])
    num = list(set(range(len(ns) + 1)).difference(ns))[0]
    fn = os.path.join(DIR_DATA, username, '%s-%d' % (label, num))
    return fn, username


def create_data_dict(data, label='default', sample_rate=500, suffix=None):
    '''
    Create a data_dict that can be saved by function `save_trials`.

    Parameters
    ----------
    data : ndarray | array list | instance of mne.Raw[Array] | dict
        1-3d array with a shape of [[num_trial x] num_channel x] window_size
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
        {'data': dict, 'label': str, 'sample_rate': int, ...}
    '''
    data_dict = {
        'label': str(label),
        'sample_rate': int(sample_rate),
        'key': 'data'
    }
    if suffix is not None:
        data_dict['suffix'] = str(suffix)

    if isinstance(data, mne.io.BaseRaw):
        data_dict['info'] = data.info
        data_dict['sample_rate'] = data.info['sfreq']
        data = data.get_data()  # num_channel x window_size
    elif isinstance(data, dict):
        dct = data
        if 'key' in dct:
            key = dct.pop('key')
        else:
            for key in ['raw', 'data', 'array']:
                if key in dct:
                    break
            else:
                raise TypeError('No data key in dict: %s' % dct.keys())
        data = np.atleast_2d(dct.pop(key))
        data_dict.update(dct)
    elif isinstance(data, (tuple, list, np.ndarray)):
        data = np.atleast_2d(data)
    else:
        raise TypeError('Invalid data type: %s' % typename(data))
    if data.ndim == 2:
        data = data[np.newaxis]
    elif data.ndim > 3:
        raise ValueError('Array with too many dimensions: %s' % data.shape)

    data_dict[data_dict['key']] = data
    return data_dict


def save_trials(username, data_dict, suffix='mat', summary=False):
    '''
    Save trials of data into ${DIR_DATA}/${username}/${label}-${num}.${suffix}

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
    >>> save_trials('test', create_data_dict(data, 'random_data', 250))
    (8, 1000) data saved to ${DIR_DATA}/test/random_data-1.mat

    >>> raw = mne.io.RawArray(data, mne.create_info(8, 250))
    >>> save_trials('test', create_data_dict(raw, format='fif.gz'))
    (8, 1000) data saved to ${DIR_DATA}/test/default-1.fif.gz
    '''
    try:
        label  = data_dict.pop('label')
        srate  = data_dict['sample_rate']
        key    = data_dict['key']
    except KeyError:
        raise TypeError('`data_dict` object created by function '
                        '`create_data_dict` is preferred.')
    else:
        suffix = data_dict.pop('suffix', suffix).strip('.')
        event  = data_dict.pop('event', [])
        info   = data_dict.pop('info', None)
        data   = data_dict.pop(key)
        data_dict['key'] = key = 'trial'

    # function create_data_dict maybe offer mne.Info object
    if 'fif' in suffix and not isinstance(info, mne.Info):
        info = mne.create_info(data.shape[1], srate)
    username = validate_datafile(username, checkname=True)[1]

    for trial in data:
        fn = '{}.{}'.format(
            validate_datafile(username, label)[0], suffix)
        try:
            if suffix == 'mat':
                data_dict[key] = trial
                # TODO: save event channel
                event
                scipy.io.savemat(fn, data_dict, do_compression=True)
            elif suffix == 'csv':
                np.savetxt(fn, trial, delimiter=',')
            elif 'fif' in suffix:
                # mute mne.io.BaseRaw.save info from stdout and stderr
                with TempStream(stdout=None, stderr=None) as ts:
                    try:
                        mne.io.RawArray(trial, info).save(fn)
                    except Exception:
                        logger.error(traceback.format_exc())
                logger.debug('%s %s' % (ts.stdout, ts.stderr))
            else:
                logger.error('format `%s` is not supported.' % suffix)
                break
            logger.info('save {} data to {}'.format(trial.shape, fn))
        except Exception:
            logger.warning('save %s failed.' % fn)
            logger.error(traceback.format_exc())
            if os.path.exists(fn):
                os.remove(fn)
    if summary:
        print('\n' + find_data_info(username)[2])


_append_keys = {}


def save_chunks(fn, data_dict, suffix='mat', append=False):
    '''
    Save chunks of data into ${DIR_DATA}/${username}/${label}-${num}.${suffix}

    Parameters
    ----------
    fn : str or file-like
    data_dict : dict
        created by function create_data_dict(data, label, format, sample_rate)
    suffix : str
        Currently supported formats are MATLAB-style '.mat'(default),
        HDF5-style '.h5' and raw text '.csv'. Format setting in
        data_dict will overwrite this argument.
    summary : bool
        Whether to print summary of currently saved data, default `False`.

    Examples
    --------
    >>> data = np.random.rand(8, 1000) # 8chs x 4sec x 250Hz data
    >>> save_trials('./test', create_data_dict(data, 'random_data', 250))
    (8, 1000) data saved to ${DIR_DATA}/test/random_data-1.mat

    >>> raw = mne.io.RawArray(data, mne.create_info(8, 250))
    >>> save_trials('test', create_data_dict(raw, format='fif.gz'))
    (8, 1000) data saved to ${DIR_DATA}/test/default-1.fif.gz
    '''
    try:
        label  = data_dict['label']
        srate  = data_dict['sample_rate']
        key    = data_dict.pop('key')
    except KeyError:
        raise TypeError('`data_dict` object created by function '
                        '`create_data_dict` is preferred.')
    else:
        suffix = data_dict.pop('suffix', suffix).lstrip('.')
        info   = data_dict.pop('info', None)
        data   = data_dict.pop(key)
        data_dict['key'] = key = 'chunk'
        data_dict[key] = data
    if isinstance(fn, string_types):
        if not fn.startswith(DIR_DATA):
            fn = os.path.join(DIR_DATA, fn)
        fobj = open(fn, 'a+b' if append else 'wb')
    elif hasattr(fn, 'name') and hasattr(fn, 'write'):
        fobj, fn = fn, fn.name
        if fobj.closed:
            raise ValueError('File object %s has already closed.' % fobj)
        append = True
    else:
        raise TypeError('Param `fn` only accepts filename or file-like object')
    try:
        if suffix == 'mat':
            if append:
                data_dict = sort_mat(fn, data_dict)
            scipy.io.savemat(fobj, data_dict, do_compression=True)
        elif 'fif' in suffix:
            # TODO: append data to fif file
            info, srate, label
        elif suffix == 'h5':
            # TODO: append data to HDF5 file
            pass
        elif suffix == 'csv':
            np.savetxt(fobj, data, delimiter=',')
        else:
            raise TypeError('format `%s` is not supported.' % suffix)
        fobj.flush()
        logger.info('save {} data to {}'.format(data_dict.keys(), fn))
    except Exception:
        logger.warning('save %s failed.' % fn)
        logger.error(traceback.format_exc())
    else:
        if not append:
            fobj.close()
    return fobj


def sort_mat(fn, data_dict):
    if fn not in _append_keys:
        try:
            data = scipy.io.loadmat(fn)
        except Exception:
            ks = []
        else:
            ks = [k for k in data.keys() if not k.startswith('_')]
            del data
        _append_keys[fn] = ks
    keys = _append_keys[fn]
    for k in list(data_dict.keys()):
        replicate = [_ for _ in keys if _.startswith(k)]
        if not replicate:
            continue
        data_dict['%s/%d' % (k, len(replicate))] = data_dict.pop(k)
    _append_keys[fn].extend(data_dict.keys())
    return data_dict


def load_mat(fn):
    if isinstance(fn, dict):
        dct = fn
    else:  # file-like object or filename
        dct = scipy.io.loadmat(fn)
    if 'trial' in dct:
        key = dct.get('key', 'trial')[0]
        data = dct.pop(key)
        if isinstance(data, dict):
            data = data['raw']
        if not isinstance(data, np.ndarray) or data.ndim != 2:
            raise IOError('Data file {} not support'.format(fn))
    elif 'chunk' in dct:
        keys = sorted(dct.keys())
        while keys:
            k = keys[0]
            if k[0] == k[-1] == '_':
                keys.remove(k)
                continue
            replst = [_ for _ in keys[1:] if _.startswith(k)] + [k]
            arrays = [dct.pop(keys.pop(keys.index(_))) for _ in replst]
            dct[k] = [arr[0] if arr.size else [] for arr in arrays]
            if isinstance(dct[k][0], (np.ndarray, list, tuple)):
                try:
                    dct[k] = np.concatenate(dct[k], -1)
                except Exception:
                    pass
        key = dct.get('key', 'chunk')[0]
        data = dct.pop(key)
    elif 'data' in dct:
        data = dct.pop('data')
    else:
        logger.error('Unrecognized mat file: %s' % dct.keys())
        raise IOError('Data file {} not support'.format(fn))
    dct['key'] = key = 'raw'
    dct[key] = data
    return dct


def load_label_data(username, label='default'):
    '''
    Load all data files that match ${DIR_DATA}/${username}/${label}-*.*

    Returns
    -------
    data_list : list
    '''
    data_list = []
    for fn in find_data_info(username)[1].get(label, []):
        name, suffix = os.path.splitext(fn)
        if suffix == '.gz':
            name, suffix = os.path.splitext(name)
        suffix = suffix.strip('.')
        try:
            if suffix == 'mat':
                dct = load_mat(fn)
                data = dct[dct['key']]
                if isinstance(data, (tuple, list)):
                    data = np.concatenate(data, -1)
            elif suffix == 'csv':
                data = np.loadtxt(fn, np.float32, delimiter=',')
            elif suffix == 'fif':
                with TempStream(stdout=None, stderr=None):
                    #  data = mne.io.RawFIF(fn).get_data()
                    data = mne.io.RawFIF(fn, preload=True)._data
            else:
                raise ValueError('format `%s` is not supported.' % suffix)
            data_list.append(data)
            logger.info('Load {} data from {}'.format(data.shape, fn))
        except Exception:
            logger.warning('Load %s failed.' % fn)
            logger.error(traceback.format_exc())
    return data_list


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
    label_dict, _, msg = find_data_info(username)
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
                for label in labels
            ])
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
        save_trials(username, summary=True, data_dict=create_data_dict(
            reader.data_frame, action, reader.sample_rate))
    return find_data_info(username)[0]


# THE END
