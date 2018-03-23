#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  6 20:45:20 2018

@author: hank
"""
# built-in
import os
import sys

# pip install numpy, scipy
import scipy.io as sio
import numpy as np

# from ./
from common import check_dir, check_input, get_label_list
from common import record_animate

@check_dir
def save_data(username,
              data,
              label,
              summary=False):
    '''
    保存数据的函数，传入参数为username,data,label(这一段数据的标签)
    可以用summary=True打印输出已经存储的数据的label及数量

    Input data shape
    ----------------
        n_sample x n_channel x window_size

    data name format:
        ${DIR}/data/${username}/${label}-${num}.${surfix}
    '''
    # check data format and shape
    if not isinstance(data, np.ndarray):
        data = np.array(data)
    if len(data.shape) != 3:
        raise IOError('Invalid data shape{}, n_sample x n_channel x '
                      'window_size is recommended!'.format(data.shape))

    label_list = get_label_list(username)[0]
    num = '1' if label not in label_list else str(label_list[label] + 1)
    fn = './data/%s/%s.mat' % (username, '-'.join([label, num]))

    print('{} data save to '.format(data.shape) + fn)
    sio.savemat(fn, {label: data}, do_compression=True)

    #==========================================================================

    # TODO: data save('.fif')

    #==========================================================================

    if summary:
        print(get_label_list(username)[1])


@check_dir
def load_data(username, summary=True):
    '''
    读取./data/username文件夹下的所有数据，返回三维数组

    Output shape: n_samples x n_channel x window_size
    '''
    if not os.listdir('./data/' + username):
        check_input(('There is no data available for this user, please save '
                     'some first, continue? '))
        return np.array([]), np.array([]), {}

    # here we got an auto-sorted action name list
    # label_list  {'left': left_num, ... , 'up': up_num, ...}
    # action_dict {'left': 10, ... , 'up': 15, ...}
    # label       [10] * left_num + ... + [15] * up_num + ...
    label_list = get_label_list(username)[0]
    action_dict = {n: a for n, a in enumerate(label_list)}

    # data  n_action*action_num*n_samples x n_channel x window_size
    # label n_action*action_num*n_samples x 1
    data = []
    label = []
    for n, action_name in enumerate(label_list):  # n_action
        for fn in os.listdir('./data/' + username):  # action_num
            if fn.startswith(action_name) and fn.endswith('.mat'):
                file_path = './data/%s/%s' % (username, fn)
                dat = sio.loadmat(file_path)[action_name]
                if len(dat.shape) != 3:
                    print('Invalid data shape{}, '
                          'n_sample x n_channel x window_size is recommended! '
                          'Skip file {}.'.format(data.shape, file_path))
                    continue
                label += dat.shape[0] * [n]  # n_samples
                data = np.stack([s for s in data] + [s for s in dat])

    #==========================================================================

    # TODO: data load('.fif')

    #==========================================================================

    if summary:
        print(get_label_list(username)[1])
    return np.array(data), np.array(label), action_dict


def save_action(username, reader):
    '''
    引导用户存储一段数据并给数据打上标签，需要username和数据流对象

    username: where will data be saved to, i.e. which folder
    reader:   where does data come from
    '''
    label_list = get_label_list(username)[0]
    while check_input('Start record action? [Y/n] '):
        record_animate(reader.sample_time)
        try:
            # reader.buffer is a dict
            action_data = [reader.buffer[ch] \
                           for ch in reader.ch_list if ch is not 'time']
            action_name = check_input(("Input action name or nothing to abort"
                                       "('-' is not allowed in the name): "),
                                      answer={})

            if action_name and '-' not in action_name:
                # input shape: 1 x n_channel x window_size
                action_data = np.array(action_data)
                action_data = action_data.reshape(1,
                                                  reader.n_channel,
                                                  reader.window_size)

                #==========================================================
                save_data(username, action_data, action_name, summary=True)
                #==========================================================

                # update label_list
                if action_name in label_list:
                    label_list[action_name] += 1
                else:
                    label_list[action_name] = 1

        except AssertionError:
            sys.exit('initialization failed')
        except Exception as e:
            print(e)
            continue
    return label_list


if __name__ == '__main__':
# =============================================================================
#     os.chdir('../')
# =============================================================================
# =============================================================================
#     username = 'test'
# =============================================================================
# =============================================================================
#     data, label, action_dict = load_data(username, summary=True)
# =============================================================================
# =============================================================================
#     save_data(username, data, 'testing', summary=True)
# =============================================================================
    
    # openbci 8-channel 250Hz
# =============================================================================
#     s = Serial_reader(250, 5, username, 1, log=True)
#     s.run()
# =============================================================================
# =============================================================================
#     p = Pylsl_reader('OpenBCI_EEG', sample_rate=250, sample_time=2, n_channel=2)
#     p.run()
# =============================================================================
    
    pass