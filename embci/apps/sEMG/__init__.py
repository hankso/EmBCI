#!/usr/bin/env python3
# coding=utf-8
#
# File: sEMG/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-02-19 01:15:57

'''__doc__'''


# built-in
from __future__ import print_function
import os
import sys
import time
import json
import traceback

from ...utils import time_stamp, check_input
from ...io import load_data, save_action


def main(username, reader, model, commander):
    # =========================================================================
    # user initializition
    # =========================================================================
    if os.listdir('./model/' + username):
        # there is trained model
        models = [i for i in sorted(os.listdir('./model/' + username))[::-1]
                  if not i.endswith('.json')]
        models.insert(0, 'new model')
        prompt = ('Please choose one to use:\n    ' +
                  '\n    '.join(['%d %s' % (n + 1, m)
                                 for n, m in enumerate(models)]) +
                  '\nmodel num(default 0): ')
        answer = {str(i): model for i, model in enumerate(models)}
        answer[''] = models[0]
        model = check_input(prompt, answer)
    else:
        # no model, then collect data and train a new one!
        model = 'new model'

    # =========================================================================
    # record data and train classifier
    # =========================================================================
    if model == 'new model':
        # no pre-saved model
        while not check_input('start record data?[Y/n] '):
            time.sleep(0)

        # ==============================================
        save_action(username, reader, ['left', 'right'])
        # ==============================================

        if not os.path.exists('./data/'+username):
            sys.exit('No data saved for training.')

        try:
            # prepare training data. n_sample x n_channel x window_size
            print('Loading data... ', end='')
            data, label, action_dict = load_data(username)
            print('done\n')

            print('Building model... ', end='')
            model.build(nb_classes=len(action_dict), input_shape=data.shape)
            model.train(data, label)
            print('done\n')

            if check_input(('Now that model is well trained, saved data is of '
                            'no use.\nIf you want to add more actions to '
                            'current model next time, please keep these data.'
                            '(not recommended)\ndelete data? [Y/n] ')):
                os.system('rm ./data/%s/*.mat' % username)

            model_name = './model/%s/%s.h5' % (username, time_stamp())
            model.save(model_name)
            with open(model_name[:-3] + '-action-dict.json', 'w') as f:
                json.dump(action_dict, f)
            print('model save to ' + model_name)
        except Exception:
            traceback.print_exc()
            sys.exit(0)
        finally:
            model_name = model_flag = data = label = f = None

        # vars:
        #     'action_dict', 'username', 'reader', 'model', 'commander'

    # =========================================================================
    # load saved classifier
    # =========================================================================
    else:
        model_name = './model/%s/%s' % (username, model_flag)
        print('loading %s ... ' % model_name, end='')
        model.load(model_name)
        with open(model_name[:-3] + '-action-dict.json', 'r') as f:
            action_dict = json.load(f)
        for i in list(action_dict.keys()):
            action_dict[int(i)] = action_dict[i]
            action_dict.pop(i)
        print('done')
        model_name = model_flag = f = i = None

    # vars:
    #     'action_dict', 'username', 'reader', 'model', 'commander'

    # =========================================================================
    # online recognizing, mainloop
    # =========================================================================
    try:
        # main thread
        while reader.isOpen():
            if not reader.streaming:
                break
            print('start recording in 2s')
            time.sleep(2)
            #  record_animate(reader.sample_time)
            class_num, class_prob = model.predict(reader.frame_data)
            action_name = action_dict[class_num]
            print('[Predict action name] ' + action_name, end='')
            print(class_prob)

            if class_prob > 0.5:
                action_cmd = commander.send('text',
                                            len(action_name),
                                            action_name)
                if action_cmd is not None:
                    print('send control command %s for action %s' % (
                          action_cmd, action_name))

    except KeyboardInterrupt:
        reader.close()
        commander.close()


# THE END
