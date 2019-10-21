#!/usr/bin/env python3
# coding=utf-8
#
# File: EmBCI/embci/utils/_event.py
# Authors: Hank <hankso1106@gmail.com>
# Create: 2019-09-18 16:47:24

'''EmBCI use JSON-based EventIO system.'''

# built-in
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os

# requirements.txt: necessary: six
from six import string_types

from . import AttributeList, AttributeDict, logger, typename
from ._json import loads, minimize

__all__ = ['Event']


class EventObject(AttributeDict):
    def __repr__(self):
        return '<Event {}>'.format(self.__string__())

    def __int__(self):
        return self.code

    def __string__(self):
        return AttributeDict.__str__(self)

    def __str__(self):
        return self.name or self.__string__()


class Event(object):
    '''Payload layer for EventIO: jsonify/unjsonify events.'''
    events = AttributeList()

    @staticmethod
    def check_event(event):
        '''
        Event 1.0 Object
        ----------------
        code: MUST be positive integer
        name: MUST be string
        desc: MAY be string | omiited
        '''
        try:
            obj  = EventObject(event)
            code = obj.get('code')
            name = obj.get('name')
        except (TypeError, ValueError):
            raise TypeError('event type cannot be `%s`' % typename(event))
        if not isinstance(code, int) or code < 0:
            raise TypeError('invalid event code: `%s`' % code)
        if not isinstance(name, string_types):
            raise TypeError('name must be string but: `%s`' % typename(name))
        return obj

    def __getitem__(self, code_or_name):
        try:
            if isinstance(code_or_name, int):
                idx = self.events.code.index(code_or_name)
            elif isinstance(code_or_name, string_types):
                idx = self.events.name.index(code_or_name)
            else:
                raise TypeError('invalid indexing type, only accept code/name')
        except ValueError:
            raise ValueError('event `%s` does not exist' % code_or_name)
        return self.events[idx]

    def __contains__(self, code_or_name):
        try:
            self[code_or_name]
        except ValueError:
            return False
        else:
            return True

    def load_file(self, fn):
        if not os.path.exists(fn):
            return False
        with open(fn, 'r') as f:
            loaded = self.load_json(f.read())
        if not loaded:
            logger.error('Load events failed from %s' % fn)
        return loaded

    def load_json(self, s):
        try:
            d = loads(s)
        except Exception:
            return False
        return self.load_event(d)

    def load_event(self, d):
        '''EventObject | dict-like | list of events'''
        if isinstance(d, (list, tuple)):
            events = list(d)
        elif isinstance(d, (dict, AttributeDict, EventObject)):
            events = d.get('events', [d])
        else:
            logger.error('Invalid event type: %s' % typename(d))
            return False
        for event in events:
            try:
                event = self.check_event(event)
            except Exception:
                continue
            if event.code in self.events.code:
                self.events.pop(self.events.code.index(event.code))
            self.events.append(event)
        return True

    def dump_event(self, v, **kwargs):
        '''Accept Event-like object or int(code) or string(name).'''
        v = v if isinstance(v, (dict, AttributeDict, EventObject)) else self[v]
        return minimize(dict(v), **kwargs)

    def dump_events(self, *args, **kwargs):
        lst = []
        if args:
            for arg in args:
                try:
                    lst.append(self[arg])
                except Exception:
                    pass
        else:
            for e in self.events:
                lst.append(dict(e))
        return minimize(lst, **kwargs)


# THE END
