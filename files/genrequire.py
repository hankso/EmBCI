#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
This script will extract magic string of requirements.txt from each python
source files found in a directory, and write modules into requirements.txt.
Modules can be sorted into different classes, such as `built-in`, `necessary`,
`replaceable` or `optional` etc. Line break is NOT allowed, multiple classes
in one line as well.

Magic string example:

# requirements.txt: aaa, bbb, ccc
# requirements.txt: foo: bar1, bar2
# requirements.txt: foo: bar3
# requirements.txt: optional: numpy, scipy
"""

from __future__ import print_function
import os
import sys


__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

REQUIRE = 'requirements.txt'
MAGICSTRING = 'requirements.txt:'


def help():
    print(__doc__)
    print('\nDirectory is needed.\nUsage:\n\tgenrequire.py ./')
    print('\tgenrequire.py . ../requirements.tmp')
    sys.exit(0)


class Module:
    def __init__(self, name, src, c=None):
        self.name = name
        self.src = src
        self.class_ = c


def scandir(dir, filter=lambda x: x.endswith('.py'), indent=0):
    print('│   ' * max(0, (indent - 1)) +
          (indent != 0) * '├── ' +
          os.path.basename(dir))
    srcfiles = []
    l = sorted(os.listdir(dir))
    while l:
        file = l.pop(0)
        filename = os.path.join(dir, file)
        # if filename.endswith(__file__):
        #     continue
        if os.path.isdir(filename):
            srcfiles += scandir(filename, indent=indent+1)
        elif os.path.isfile(filename):
            if filter(filename):
                print(('│   ' if len(l) else '│   ') * indent +
                      ('├── ' if len(l) else '└── ') + file, end=' selected\n')
                srcfiles.append(filename)
            else:
                print(('│   ' if len(l) else '│   ') * indent +
                      ('├── ' if len(l) else '└── ') + file, end=' skip\n')
    return srcfiles


def extmod(file):
    print('extracting modules from {}: '.format(file), end='')
    modules = []
    with open(file, 'r') as f:
        for line in f:
            if not line.startswith('#'):
                continue
            if MAGICSTRING not in line:
                continue
            line = line[line.index(MAGICSTRING) + len(MAGICSTRING):].strip()
            if ':' in line:
                i = line.index(':')
                c, line = line[:i].strip(), line[i+1:].strip()
            else:
                c = None
            ms = [Module(m.strip(), file, c) for m in line.split(',')]
            if len(ms):
                print(' '.join(map(lambda m: m.name, ms)), end=' ')
                modules += ms
    print()
    return modules


def sortmod(modules):
    classes = {'_conflict': {}}
    while modules:
        m = modules.pop()
        for module in modules:
            if m.name != module.name:
                continue
            if m.class_ != module.class_:
                if m.name not in classes['_conflict']:
                    classes['_conflict'][m.name] = []
                classes['_conflict'][m.name].append(module)
            modules.remove(module)
        if m.name in classes['_conflict']:
            classes['_conflict'][m.name].append(m)
        else:
            if m.class_ not in classes:
                classes[m.class_] = []
            classes[m.class_].append(m)
    return classes


if __name__ == '__main__':
    if len(sys.argv) < 2:
        help()
    d = os.path.abspath(sys.argv[1])
    if not os.path.exists(d) or not os.path.isdir(d):
        help()

    if len(sys.argv) > 2:
        REQUIRE = sys.argv[2]

    srcfiles = scandir(d)

    modules = reduce(
        lambda f1, f2: \
            (f1 + extmod(f2)) if isinstance(f1, list) else \
            (extmod(f1) + extmod(f2)),
        srcfiles)

    classes = sortmod(modules)

    header = (
        '#\n# EmBCI Python module requirements.txt\n'
        '#\n# Automatically generated file\n#\n\n')

    body = '\n'.join([m.name for m in classes.pop(None, [])]) + '\n\n'

    conflicts = ''
    if classes['_conflict']:
        conflicts += '# [conflicts]\n\n' + '\n\n'.join([
            '\n'.join(['# [{}] from {}\n{}'.format(m.class_, m.src, m.name)
                       for m in l])
            for l in classes['_conflict'].values()]) + '\n\n'
    classes.pop('_conflict')

    for c in classes:
        body += '# [{}]\n'.format(c)
        body += '\n'.join([m.name for m in classes[c]])
        body += '\n\n'

    if os.path.exists(REQUIRE):
        os.rename(REQUIRE, REQUIRE + '.bak')
    with open(REQUIRE, 'w') as f:
        print(header + body + conflicts, file=f)
