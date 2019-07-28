#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/io/base.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Sat 16 Mar 2019 19:37:41 CST

'''Save and Load Utilities'''

# built-in
import os
import re
import sys
import time
import traceback

# requirements.txt: data-processing: numpy, scipy
# requirements.txt: bio-signal: mne
import numpy as np
import scipy.io
import mne

from ..utils import mkuserdir, check_input, TempStream
from ..configs import DATADIR
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
    ${DATADIR}/${username}/${label}-${num}.${suffix}

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
    for filename in sorted(os.listdir(os.path.join(DATADIR, username))):
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
    summary = '\nThere are {} actions with {} data recorded.'.format(
        len(label_dict), sum(label_dict.values()))
    if label_dict:
        maxname = max([len(_) for _ in label_dict]) + 8
        summary += (
            '\n  * ' + '\n  * '.join([k.ljust(maxname) + str(label_dict[k]) +
                                      '\n    ' + '\n    '.join(name_dict[k])
                                      for k in label_dict]))
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
def save_data(username, data_dict, suffix='.mat', summary=False):
    '''
    Save data into ${DATADIR}/${username}/${label}-${num}.${suffix}

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
    (8, 1000) data saved to ${DATADIR}/test/random_data-1.mat

    >>> raw = mne.io.RawArray(data, mne.create_info(8, 250))
    >>> save_data('test', create_data_dict(raw, format='fif.gz'))
    (8, 1000) data saved to ${DATADIR}/test/default-1.fif.gz
    '''
    try:
        label = data_dict['label']
        sample_rate = data_dict['sample_rate']
    except Exception as e:
        raise TypeError('{} {}\n`data_dict` object created by function '
                        '`create_data_dict` is suggested.'.format(
                            e.__class__.__name__.lower(), e.args[0]))

    # scan how many data files already there
    label_dict = get_label_dict(username)[0]
    num = label_dict.get(label, 0) + 1
    suffix = data_dict.pop('suffix', suffix)
    # function create_data_dict maybe offer mne.Info object
    info = data_dict.pop(
        'info', mne.create_info(data_dict['data'].shape[1], sample_rate))
    data = data_dict.pop('data', [])

    for sample in data:
        fn = os.path.join(
            DATADIR, username, '{}-{}{}'.format(label, num, suffix))
        num += 1
        try:
            if suffix == '.mat':
                data_dict['data'] = sample
                scipy.io.savemat(fn, data_dict, do_compression=True)
            elif suffix == '.csv':
                np.savetxt(fn, sample, delimiter=',')
            elif suffix in ['.fif', '.fif.gz']:
                # mute mne.io.BaseRaw.save info from stdout and stderr
                with TempStream(stdout=None, stderr=None):
                    mne.io.RawArray(sample, info).save(fn)
            else:
                raise ValueError('format `%s` is not supported.' % suffix)

            logger.info('Save {} data to {}'.format(sample.shape, fn))
        except Exception:
            if os.path.exists(fn):
                os.remove(fn)
            num -= 1
            logger.warning('Save {} failed.\n{}'.format(
                fn, traceback.format_exc()))

    if summary:
        print(get_label_dict(username)[1])


def load_label_data(username, label='default'):
    '''
    Load all data files that match ${DATADIR}/${username}/${label}-*.*

    Parameters
    ----------
    username : str
    label : str

    Returns
    -------
    data_list : list
    '''
    data_list = []
    userdir = os.path.join(DATADIR, username)
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
    Load all data files under directory ${DATADIR}/${username}

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
    >>> data.shape, label
    ((5, 8, 1000), ['default', 'default', 'default', 'right', 'left'])

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
      + left     1
      + right    1
    '''
    data_array = []
    label_list = []
    action_dict, msg = get_label_dict(username)

    def filterer(action):
        if isinstance(pick, str):
            return action == pick
        if isinstance(pick, (tuple, list)):
            return action in pick
        if isinstance(pick, re._pattern_type):
            return bool(pick.match(action))
        if callable(pick):
            return pick(action)
        return True

    actions = filter(filterer, action_dict)
    for action in actions:
        data_list = load_label_data(username, action)
        data_array.extend(data_list)
        label_list.extend([action] * len(data_list))

    if summary:
        msg += '\nThere are {} actions with {} data loaded.'.format(
            len(actions), len(data_array))
        if len(data_array):
            maxname = max([len(_) for _ in actions]) + 4
            msg += ('\n  + ' + '\n  + '.join(
                [action.ljust(maxname) + str(label_list.count(action))
                 for action in actions]))
        print(msg.strip())

    if len(data_array):
        data_array = np.array(data_array)
    # data_array: n_samples x num_channel x window_size
    # label_list: n_samples
    return data_array, label_list


def save_action(username, reader, action_list=['relax', 'grab']):
    '''
    引导用户存储一段数据并给数据打上标签，需要username和reader数据流对象

    username: where will data be saved to
    reader:   where does data come from
    '''
    print('\nYou have to finish each action in {} seconds.'.format(
        reader.sample_time))
    rst = check_input(('How many times you would like to record for each '
                       'action?(empty to abort): '), {}, times=999)
    if not rst:
        return
    try:
        num = int(rst)
    except ValueError:
        return
    label_list = get_label_dict(username)[0]
    name_list = action_list * num
    np.random.shuffle(name_list)
    for i in range(len(action_list) * num):
        action_name = name_list.pop()
        print('action name: %s, start recording in 2s' % action_name)
        time.sleep(2)
        try:
            if action_name and '-' not in action_name:
                # input shape: 1 x num_channel x window_size
                save_data(username, reader.data_frame, action_name,
                          reader.sample_rate, print_summary=True)
                # update label_list
                if action_name in label_list:
                    label_list[action_name] += 1
                else:
                    label_list[action_name] = 1
            print('')
            time.sleep(2)
        except AssertionError:
            sys.exit('initialization failed')
        except Exception as e:
            print(e)
            continue
    return label_list


# THE END
