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
import sys
sys.path += ['../utils']

# pip install numpy
import numpy as np

# from ../utils
from common import time_stamp, check_input, first_use, record_animate
from IO import load_data, save_action


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
        print(('\nYou have to finish each action in '
               '{} seconds.').format(reader.sample_time))
        
        #==========================================
        action_list = save_action(username, reader)
        #==========================================
        
        while len(os.listdir('./data/'+username)) < 15 * len(action_list):
            if check_input('Please record more data and actions: [Y/n] '):
            
                #==========================================
                action_list = save_action(username, reader)
                #==========================================
                
            else:
                break
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
            model_name = action_list = model_flag = data = label = f = None
        
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
    print('now start online recognizing...')
    while reader.isOpen():
        if not reader.streaming:
            break
        print('start recording in 2s')
        time.sleep(2)
        record_animate(reader.sample_time)
        data = np.array(
                [reader.buffer[ch][-reader.window_size:] \
                 for ch in reader.buffer if ch is not 'time']
            ).reshape(1, reader.n_channel, reader.window_size)
        # here input shape: 1 x n_channel x window_size
        class_num, action_prob = model.predict(data)
        
        # you can redirect this predicted result(string) to any output
        action_name = action_dict[class_num]
# =============================================================================
#         print('[Predict action name] ' + action_name)
# =============================================================================
        if action_prob > 0.6:
            action_cmd = commander.send(action_name, action_prob)
            if action_cmd:
                print('sending control command %s for action %s' % (
                        action_cmd, action_name))


def P300(username, reader, model, commander):
    raise NotImplemented
    
def SSVEP():
    raise NotImplemented
    
def TGAM_relax(username, reader, model, commander):
    raise NotImplemented
    
def MotorImaginary(username, reader, model, commander):
    raise NotImplemented