#!/usr/bin/env python3
# coding=utf-8
#
# File: Speller/__init__.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-06-25 23:06:31

'''
Website User Interface based Steady State Visual Evoked Potential Speller.

Implemented on embedded platform (ARM device) within EmBCI.

APIs
----
`sess/init` : schedule a session containing:
    1. browser send session.init event or GET /sess/start
    2. server start recording data and broadcast mark by pylsl outlet
    3. server send recorder.start event
    4. browser enable flickers on receiving recorder.start
    5. browser disable flickers after task done
    6. browser send session.end event or GET /sess/stop
    7. server start generate result on receiving session.end
    8. server send session.result event indicating result ready
    9. browser fetch result when session.result or by looply GET /sess/result
`sess/end` : legacy interface to end the session
`sess/result` : legacy interface to fetch the prediction result
`event` :
    'GET' send event to server by query string
    'POST' ask server to broadcast event with name by data
`event/ws` : EventIO WebSocket connection point
`event/update` :
`event/list` : get EventIO event list
`kbd/layout`
`kbd/layout/<name>` => {
        'name': '/path/to/layout-filename.json',
        'blocks': [
            {
                'name': 'alphabet',
                'freq': in Herz, 'phase': multiple of Pi in rad,
                'x': coordinate, 'y': in pixel,
                'w': width, 'h': height,
            },
            {'name': 'q', 'x': 0, 'y': 1.0, 'freq': 8.0, 'phase': 1.50Pi},
            {'name': 'w', 'x': 2.0, 'y': 1.0, 'freq': 9.0, 'phase': 1.75Pi},
            ...
        ]
    }
'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os
import glob
import time
import json
import random
import string
import traceback
import threading

# requirements.txt: network: bottle, gevent-websocket
# requirements.txt: data: numpy
# requirements.txt: necessary: six
import pylsl
import bottle
import numpy as np
from six import string_types
from geventwebsocket.websocket import WebSocketError

from embci.utils import (
    config_logger, random_id, null_func,
    Event, AttributeDict
)
from embci.io import LSLReader as Reader, find_data_info, load_mat
from embci.apps.recorder import Recorder

from .model import Model

# =============================================================================
# constants

__basedir__ = os.path.dirname(os.path.abspath(__file__))
__layouts__ = os.path.join(__basedir__, 'layouts')
__events__  = os.path.join(__basedir__, 'events.json')

speller = bottle.Bottle()
results = {}
wslist = []
logger = config_logger(__name__)
reader = model = event = outlet = wsevent = recorder = rec_lock = None


# =============================================================================
# SSVEP WebUI EventIO

@speller.route('/event/ws')
def event_websocket():
    ws = bottle.request.environ.get('wsgi.websocket')
    if ws is None:
        bottle.abort(400, 'WebSocket request expected.')
    wslist.append(ws)
    ADDR = '{REMOTE_ADDR}:{REMOTE_PORT}'.format(**ws.environ)
    logger.info('Event websocket connected from ' + ADDR)
    event_update()             # Is this my turn?
    while not ws.closed:
        if ws is not wsevent:  # No, it's not.
            time.sleep(2)
            continue
        try:                   # I will never give away my shot.
            msg = ws.receive()
            if msg is None:
                break
            event_handle(msg)
        except WebSocketError:
            ws.close()
        except Exception:
            logger.error(traceback.format_exc())
    wslist.remove(ws)
    logger.info('Event websocket from %s closed' % ADDR)
    event_update()


@speller.route('/event/update')
def event_update():
    '''If last ws is removed from wslist, point wsevent to the next one.'''
    global wsevent
    if wsevent in wslist:      # There is one client blocking the queue.
        return False
    elif len(wslist):          # Point to next client, continue wait in line.
        wsevent = wslist[0]
        event_send('misc.unlock')
        return False
    else:                      # No others in font of you, show the webpage!
        return True


@speller.route('/event/list')
def event_list():
    fn = bottle.request.query.get('filename', __events__)
    event.load_file(fn)
    return event.dump_events()


@speller.get('/event')
def event_handle(es=None):
    if es is None:
        es = bottle.request.params.get('event')  # None | '' | '...'
    elif not isinstance(es, string_types):
        raise TypeError('Invalid event type: `%s`' % type(es).__name__)
    try:
        obj = event.check_event(json.loads(es))
    except Exception as e:
        bottle.abort(400, 'Invalid event: `%s`' % e)
    else:
        logger.debug('Received event: `%s`' % obj)
    if '.' in obj.name:
        name = obj.name.split('.')
        hdlr = globals().get('event_handle_' + name[0], event_handle_default)
        name = '.'.join(name[1:])
    else:
        name = obj.name
        hdlr = event_handle_default
    threading.Thread(target=hdlr, args=(name, obj)).start()


@speller.post('/event')
def event_send(en=None, **extra):
    if wsevent not in wslist:
        return
    if en is None:
        en = (
            bottle.request.POST.get('name') or
            int(bottle.request.POST.get('code', 0))
        )
    if isinstance(en, string_types + (int, )):
        try:
            en = event[en]
        except ValueError:
            bottle.abort(400, 'Invalid event: `%s`' % en)
    elif not isinstance(en, (dict, AttributeDict)):
        bottle.abort(400, 'Invalid event type: `%s`' % type(en).__name__)
    ed = dict(en)
    if extra:
        ed.update(extra)
    try:
        msg = event.dump_event(ed)
    except Exception:
        pass
    else:
        logger.info('Sending event: `%s`' % msg)
        wsevent.send(msg)


def event_handle_default(cmd, obj):
    msg = 'Unhandled event: `%s`' % obj
    logger.error(msg)
    bottle.abort(400, msg)


def event_handle_train(cmd, obj):
    if cmd == 'start':
        model_train()
    elif cmd == 'init':
        if not rec_lock.acquire(False):
            return
        recorder.resume()
        recorder.event = obj.code
    elif cmd == 'end':
        recorder.event = obj.code
        recorder.pause()
        recorder.save()
        if rec_lock.locked():
            rec_lock.release()


def event_handle_session(cmd, obj):
    if wsevent not in wslist:  # called by GET /event?query
        bottle.abort(400, 'This API is for EventIO only.')
    if cmd == 'start':  # real start time stamp
        recorder.event = obj.code
        outlet.push_sample([obj.code], time.time())
    elif cmd == 'stop':  # real stop time stamp
        recorder.event = obj.code
        outlet.push_sample([obj.code], time.time())
    elif cmd == 'init':
        if not rec_lock.acquire(False):
            return
        session_init(wsevent, obj)
    elif cmd == 'end':
        session_end(wsevent, obj)
        if rec_lock.locked():
            rec_lock.release()
    elif cmd == 'alphabet':  # cue on specific alphabet for training
        code = ord(obj.char) << 16 | obj.code
        recorder.event = code
        outlet.push_sample([code], time.time())
    else:
        bottle.abort(400, 'Invalid command ' + cmd)


# =============================================================================
# SSVEP Experiment Session

@speller.get('/sess/config')
def session_config(**kwargs):
    for key, value in (kwargs or bottle.request.query).items():
        if key == 'task':
            if value == 'trial':
                recorder.chunk = False
                recorder.event_merge = False
            elif value == 'train':
                recorder.chunk = 3
                recorder.event_merge = True
        elif key == 'timeout':
            model.update_config({
                'nsample': int(float(value) / 1000 * model.srate),
            })
        else:
            bottle.abort('Unknown configuration: {}-{}'.format(key, value))


@speller.get('/sess/start')
def session_start(ID=None, timeout=None):
    ID = ID or bottle.request.query.get('id') or random_id(6)
    timeout = timeout or bottle.request.query.get('timeout')
    if timeout:
        try:
            timeout = int(timeout)
            assert timeout > 0
            threading.Timer(timeout, session_stop, args=(ID, )).start()
        except ValueError:
            pass
        except AssertionError:
            bottle.abort(400, 'Invalid timeout value: %s' % timeout)
    if not rec_lock.acquire(False):
        return
    recorder.resume()
    outlet.push_sample([event['recorder.start'].code], time.time())
    return {'recorder.start': ID}


@speller.get('/sess/stop')
def session_stop(ID=None, result=None):
    ID = ID or bottle.request.query.get('id')
    if not ID:
        bottle.abort(400, 'Session stop without an ID')
    result = result or bottle.request.query.get('result', False)
    recorder.pause()
    if rec_lock.locked():
        rec_lock.release()
    if result and recorder.username:
        data = recorder.data_all
        if data is not None:
            model_predict(data, ID)
    return {'recorder.stop': ID}


def session_init(ID, obj):
    if not recorder.chunk:
        recorder.resume()
    code = event['recorder.start'].code
    outlet.push_sample([code], time.time())
    event_send(code)
    return 'session initialized'  # return value is optional


def session_end(ID, obj):
    if not recorder.chunk:
        recorder.pause()
    if obj.result and recorder.username:
        data = recorder.data_all
        if data is not None:
            model_predict(data, wsevent)
    return 'session ended'  # return value is optional


@speller.get('/sess/result')
def session_result():
    '''
    If prediction result is not generated yet, front-end code should
    handle the error.
    '''
    ID = bottle.request.query.get('id') or wsevent
    if ID not in results:
        bottle.abort(400, 'Invalid id: %s' % ID)
    return {'index': results.pop(ID).tolist()}


# =============================================================================
# Model training

@speller.route('/model/datafiles')
def model_train_datafiles():
    if not recorder.username:
        bottle.abort(400, 'Username not set yet!')
    name_dict = find_data_info(recorder.username)[1]
    if recorder.name not in name_dict:
        bottle.abort(400, 'No data recorded for %s' % recorder.username)
    return {'datafiles': name_dict[recorder.name]}


@speller.route('/model/train')
def model_train(fns=None):
    fns = fns or model_train_datafiles()['datafiles']
    raws, labels = model_extract_data(load_mat(fns[-1]))
    traindata = {}
    for n, label in enumerate(labels):
        if label not in traindata:
            traindata[label] = []
        traindata[label].append(raws[n])
    bylabel = list(map(len, traindata.values()))
    if np.std(bylabel) or len(bylabel) != model.ntarget:
        bottle.abort(500, 'Data trials are not constant: %s' % labels)
    # n_target x n_trial x n_channel x n_sample
    traindata = np.array([traindata[key] for key in sorted(traindata)])
    # n_target x n_channel x n_sample x n_trial
    traindata = traindata.transpose(0, 2, 3, 1)
    threading.Thread(target=model_train_func, args=(traindata, )).start()


def model_train_func(data):
    event_send('train.start')
    model.train(data, callback=lambda v: event_send(
        'train.progress', progress=float(v)
    ))
    event_send('train.stop')


@speller.route('/model/config')
def model_config(**kwargs):
    model.update_config(**(kwargs or bottle.request.query))


def model_extract_data(dct):
    key = dct.get('key', 'raw')
    raw = dct[key]
    if 'event' in dct and dct['event']:
        es = dct['event']
        raw, ts = raw[:-1], raw[-1]
    else:
        raw, es, ts = raw[:-2], raw[-2:], raw[-1]
    labels = []
    snips = []
    for e, t in es.T[np.where(es[0])[0]]:
        if int(e) & 0xffff == int(event['session.alphabet']):
            labels.append(int(e) >> 16)
    if es[0].any():
        idxsa = np.where(es[0] == int(event['session.start']))[0]
        idxso = np.where(es[0] == int(event['session.stop']))[0]
        for i in range(min(len(idxsa), len(idxso))):
            if es.shape[-1] == raw.shape[-1]:
                tsa, tso = idxsa[i], idxso[i]
            else:
                tsa = abs(ts - es[-1, idxsa[i]]).argmin()
                tso = abs(ts - es[-1, idxso[i]]).argmin()
            snip = model.resize(raw[:, tsa:tso])
            snips.append(snip)
    if not len(snips):
        snips.append(model.resize(raw))
    lendiff = len(snips) - len(labels)
    if lendiff < 0:
        labels = labels[:lendiff]
    else:
        #  labels.extend([labels[0]] * lendiff)
        labels.extend([0] * lendiff)
    return snips, labels


def model_predict(data, ID=None):
    threading.Thread(target=model_predict_func, args=(data, ID)).start()


def model_predict_func(data, ID):
    raw = model_extract_data(data)[0]
    results[ID] = model.predict(raw)
    event_send('session.result')


# =============================================================================
# SSVEP Flickers Layout

@speller.get('/kbd/layout')
def keyboard_layout_list():
    layouts = glob.glob(os.path.join(__layouts__, '*.json'))
    return json.dumps([
        os.path.splitext(os.path.basename(_))[0]
        for _ in layouts
    ] + ['random'])


@speller.get('/kbd/layout/random')
def keyboard_layout_random(name='random'):
    alphabets = list(string.ascii_lowercase + string.digits + ' ,.<')
    random.shuffle(alphabets)
    return {'name': name, 'width': 800, 'height': 500, 'blocks': [
        {
            'name': a, 'w': 70, 'h': 70,
            'x': 50 + (n % 8) * 100, 'y': 50 + (n // 8) * 100,
            'freq': random.choice(np.arange(8, 16, 0.2)),
            'phase': random.choice(np.arange(0, 14, 0.35) % 2) * np.pi,
        } for n, a in enumerate(alphabets)
    ]}


@speller.get('/kbd/layout/<name>')
def keyboard_layout_load(name):
    '''
    If the layout file doesn't exist or fail to be loaded, let's fallback
    to generate one random layout.
    '''
    # JFPM Function: y = A * sin(B * (x - C)) + D
    # B = freq * 2Pi
    # C = phase / B = phase / (freq * 2Pi)
    if name not in keyboard_layout_list():
        bottle.abort(400, 'Invalid layout name: ' + name)
    name = os.path.join(__layouts__, name + '.json')
    try:
        with open(name, 'r') as f:
            layout = json.load(f)
    except Exception:
        logger.error(traceback.format_exc())
        layout = keyboard_layout_random()
    model.update_config(targets=[b['freq'] for b in layout['blocks']])
    return layout


# =============================================================================
# Initialization & webpage hosting

def app_init():
    global reader, model, event, outlet, recorder, rec_lock, app_init
    reader = Reader(250, 5, 8)
    reader.start(type='Reader Outlet', method='process')
    time.sleep(0.2)
    model = Model(reader.sample_rate, reader.num_channel,
                  reader.window_size, range(40))
    event = Event()
    assert event.load_file(__events__)
    outlet = pylsl.StreamOutlet(pylsl.StreamInfo(
        'EventIO', 'event', channel_format='int32', source_id=random_id()))
    recorder = Recorder(reader, chunk=False, event_merge=False)
    recorder.start()
    rec_lock = threading.Lock()
    app_init = null_func


@speller.route('/')
def app_root():
    if event_update():
        app_init()
    bottle.redirect('index.html')


@speller.route('/index.html')
@bottle.view(os.path.join(__basedir__, 'index.html'))
def app_index():
    '''
    Mask whole webpage by setting CSS of mask layer to `display: block;`
    in case of multiple accessing.
    '''
    if 'username' in bottle.request.query:
        recorder.username = bottle.request.query.get('username')
    return {'display': 'none' if event_update() else 'block'}


@speller.route('/rec/<command>')
def app_recorder_hook(command):
    if not rec_lock.acquire(False):
        bottle.abort(500, 'Recorder is busy')
    rst = recorder.cmd(command)
    if rec_lock.locked():
        rec_lock.release()
    return rst


@speller.route('/lock/<method>')
def app_recorder_lock(method):
    return str(getattr(rec_lock, method, null_func)())


@speller.route('/srv/<filename:path>')
def app_static_hook(filename):
    return bottle.HTTPError(404, 'File does not exist.')


@speller.route('/<filename:path>')
def app_static_files(filename):
    if os.path.exists(os.path.join(__basedir__, filename)):
        return bottle.static_file(filename, __basedir__)
    bottle.redirect('/srv/' + filename)


application = speller
__all__ = ['application']
# THE END
