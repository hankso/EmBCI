#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 27 14:36:27 2018

@author: hank
"""
# built-in
from __future__ import print_function
import os
import time
import json
import threading
import sys
sys.path += ['../utils']

# pip install numpy
import numpy as np
import matplotlib.pyplot as plt; plt.ion()

# from ../utils
from common import time_stamp, check_input, first_use, record_animate, Timer
from IO import load_data, save_action
from signal_info import Signal_Info
#from visualization import view_data_with_matplotlib


def sEMG(username, reader, model, commander):
    #==========================================================================
    
    # user initializition
    
    #==========================================================================
    if not os.path.exists('./models/' + username):
        # no this user before
        try:
            os.mkdir('./models/' + username)
            os.mkdir('./data/' + username)
        except:
            pass
        model_flag = True
    elif os.listdir('./models/' + username):
        # there is trained models
        print('found saved model:', end='')
        models = [i for i in sorted(os.listdir('./models/' + username))[::-1] \
                  if not i.endswith('.json')]
        prompt = ('choose one to use:\n    %s\n    0\trecord '
                  'action data and train a new model\nnum: ') % \
                  '\n    '.join('%d\t%s'%(n+1, m) for n,m in enumerate(models))
        answer = {str(i+1): models[i] for i in range(len(models))}
        answer.update({'0': True})
        model_flag = check_input(prompt, answer)
        models = prompt = answer = None
    else:
        # no model, then collect data and train a new one!
        model_flag = True
    
    # we must clear workspace frequently on orangepi, which only has 512MB RAM
    # variables existing:
    #     'model_flag', 'username', 'reader'
    
    
    #==========================================================================
    
    # record data and train classifier
    
    #==========================================================================
    if model_flag is True:
        # no pre-saved model
        if not first_use():
            sys.exit('terminated')
        while not check_input('start record data?[Y/n] '):
            pass
        
        #===============================================
        save_action(username, reader, ['left', 'right'])
        #===============================================

        if not os.path.exists('./data/'+username):
            sys.exit('No data saved for training.')
        
        try:
            # prepare training data. n_sample x n_channel x window_size
            print('Loading data... ', end='')
            data, label, action_dict = load_data(username)
            print('done\n')
            
            print('Building model... ', end='')
            model.build(nb_classes = len(action_dict),
                        input_shape = data.shape)
            model.train(data, label)
            print('done\n')
            
            if check_input(('Now that model is well trained, saved data is of '
                            'no use.\nIf you want to add more actions to '
                            'current model next time, please keep these data.'
                            '(not recommended)\ndelete data? [Y/n] ')):
                os.system('rm ./data/%s/*.mat' % username)
                
            model_name = './models/%s/%s.h5' % (username, time_stamp())
            model.save(model_name)
            with open(model_name[:-3] + '-action-dict.json', 'w') as f:
                json.dump(action_dict, f)
            print('model save to ' + model_name)
        except Exception as e:
            print(e)
            sys.exit(0)
        finally:
            model_name = model_flag = data = label = f = None
        
        # vars:
        #     'action_dict', 'model', 'reader', 'username'
            
            
    #==========================================================================
    
    # load saved classifier
    
    #==========================================================================
    else:
        model_name = './models/%s/%s' % (username, model_flag)
        print('loading %s ... ' % model_name, end='')
        model.load(model_name)
        with open(model_name[:-3] + '-action-dict.json', 'r') as f:
            action_dict = json.load(f)
        for i in list(action_dict.keys()):
            action_dict[int(i)] = action_dict[i]
            action_dict.pop(i)
        print('done')
        time.sleep(reader.sample_time)
        model_name = model_flag = f = i = None
    
    # vars:
    #     'action_dict', 'model', 'reader', 'username'
        

    #==========================================================================
    
    # online recognizing, mainloop
    
    #==========================================================================
    display_ch = 'channel0'
    def draw_point(pause_flag, stop_flag, lock):
        while not stop_flag.isSet():
            pause_flag.wait()
            d = np.array(reader.buffer[display_ch][-10:]) * 48 + 16
            lock.acquire()
            commander.send('points', len(d), bytearray(d.astype(np.uint8)))
            lock.release()
#    pause_flag = threading.Event(); pause_flag.set()
#    stop_flag = threading.Event(); stop_flag.clear()
#    lock = threading.Lock()
#    t = threading.Thread(target=draw_point, args=(pause_flag, stop_flag, lock))
#    t.setDaemon(True)
#    t.start()
    si = Signal_Info()
    try:
        last_time = time.time()
        while 1:
            while (time.time() - last_time) < 1.0:
                time.sleep(0.1)
            last_time = time.time()
            data = reader.buffer[display_ch]
            plt.clf()
            plt.subplot(221); plt.plot(data)
            psd = np.concatenate((si.fft(data, reader.sample_rate)[1][0]**2, [0] * 3))
            plt.subplot(222); plt.plot(np.log10(psd))
#            psd = psd / psd.max() * 48 + 16
#            commander.send('points', 128, bytearray(psd.astype(np.uint8)))
            max_freq, max_amp = si.peek_extract(data, 4, 6, reader.sample_rate)[0]
            plt.subplot(223); plt.title('max energy %f at %fHz' % (max_amp, max_freq))
            print('4-6Hz频段能量最大频率为%dHz, 其幅值为%f' % (max_freq, max_amp))
            
    except KeyboardInterrupt:
        reader.close()
        commander.close()
    '''
    try:
        while reader.isOpen():
            if not reader.streaming:
                break
            print('start recording in 2s')
            time.sleep(2)
            record_animate(reader.sample_time)
            class_num, class_prob = model.predict(
                    reader.channel_data().reshape(1,
                                                  reader.n_channel,
                                                  reader.window_size))
            action_name = action_dict[class_num]
            print('[Predict action name] ' + action_name)
            print(class_prob)
            
            if class_prob > 0.5:
                lock.acquire()
                time.sleep(1.0/25.0)
                action_cmd = commander.send('text',
                                            len(action_name),
                                            action_name)
                lock.release()
                if action_cmd is not None:
                    print('send control command %s for action %s' % (
                            action_cmd, action_name))
    except KeyboardInterrupt:
        reader.close()
        commander.close()
        stop_flag.set()
    '''

def P300(username, reader, model, commander):
    raise NotImplemented
    
def SSVEP():
    raise NotImplemented
    
def TGAM_relax(username, reader, model, commander):
    raise NotImplemented
    
def MotorImaginary(username, reader, model, commander):
    raise NotImplemented