#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
import os
import sys
import argparse
import subprocess

from functools import reduce

HELP = '''
This script will extract magic string of requirements.txt from each python
source files found in a directory, and write modules into requirements.txt.
Modules can be sorted into different classes, such as `built-in`, `necessary`,
`replaceable` or `optional` etc. Line break is NOT allowed, multiple classes
in one line as well.
'''

EXAMPLE = '''
Magic string example:

# requirements.txt: aaa, bbb, ccc
# requirements.txt: foo: bar1, bar2
# requirements.txt: foo: bar3
# requirements.txt: optional: numpy, scipy

Usage example:
    genrequire ./ -v
    genrequire src/ utils/ tools/ -o requirements.txt
'''

__dir__ = os.path.dirname(os.path.abspath(__file__))
__file__ = os.path.basename(__file__)

MAGICSTRING = 'requirements.txt:'
OUTPUT = sys.stdout
VERBOSE = 0


class Module(str):
    def __new__(cls, name, src, type=None):
        obj = str.__new__(cls, name)
        obj.name = name
        obj.srcfile = src
        obj.type = type
        return obj

    def __str__(self):
        return '<module {}:{type} @ {srcfile}>'.format(
            repr(self), **self.__dict__)


def python_filter(filename):
    '''
    Check if file is python script by linux/unix command `file`
    '''
    return 'text/x-python' in subprocess.check_output(['file', '-i', filename])
    #  return 'Python script' in subprocess.check_output(['file', filename])


def scandir(dir, cond=lambda x: x.endswith('.py'), indent=0):
    if VERBOSE:
        print('│   ' * max(0, (indent - 1)) +
              (indent != 0) * '├── ' +
              os.path.basename(dir))
    srcfiles = []
    l = sorted(os.listdir(dir))
    while l:
        file = l.pop(0)
        filename = os.path.join(dir, file)
        if filename.endswith(__file__):
            continue
        if os.path.isdir(filename):
            srcfiles += scandir(filename, indent=indent+1)
        elif os.path.isfile(filename):
            if cond(filename):
                srcfiles.append(filename)
                log = ' selected\n'
            else:
                log = ' skip\n'
            if VERBOSE:
                print(('│   ' if len(l) else '│   ') * indent +
                      ('├── ' if len(l) else '└── ') + file, end=log)
    return srcfiles


def extmod(file):
    if VERBOSE:
        print('extracting modules from {}: '.format(file), end='')
    modules = []
    with open(file, 'r') as f:
        for line in [_ for _ in f if _.startswith('#') and MAGICSTRING in _]:
            line = line[line.index(MAGICSTRING) + len(MAGICSTRING):].strip()
            if ':' in line:
                i = line.index(':')
                c, line = line[:i].strip(), line[i+1:].strip()
            else:
                c = None
            ms = [Module(m.strip(), file, type=c) for m in line.split(',')]
            if len(ms):
                modules += ms
            if VERBOSE:
                print(' '.join(ms), end=' ')
    if VERBOSE:
        print('\n')
    return modules


def sortmod(modules):
    classes = {'_conflict': {}}
    while modules:
        m = modules.pop()
        for sm in [_ for _ in modules if m == _]:
            modules.remove(sm)
            if m.type != sm.type:
                if m not in classes['_conflict']:
                    classes['_conflict'][m] = []
                classes['_conflict'][m].append(sm)
        if m in classes['_conflict']:
            classes['_conflict'][m].append(m)
        else:
            if m.type not in classes:
                classes[m.type] = []
            classes[m.type].append(m)
    return classes


def genrequire(dirs):
    srcfiles = []
    for d in dirs:
        if os.path.exists(d) and os.path.isdir(d):
            srcfiles += scandir(d, cond=python_filter)

    modules = reduce(
        lambda f1, f2:
            (f1 + extmod(f2)) if isinstance(f1, list) else
            (extmod(f1) + extmod(f2)),
        srcfiles)

    classes = sortmod(modules)

    header = (
        '#\n# EmBCI Python module requirements.txt\n'
        '#\n# Automatically generated file\n#\n\n')

    body = '\n'.join(classes.pop(None, [])) + '\n\n'

    conflicts = ''
    if classes['_conflict']:
        conflicts += '#\n# [conflicts]\n# You may manually solve them.\n#\n\n'
        conflicts += '\n\n'.join([
            '\n\n'.join([
                '# From {}\n# [{}]\n'.format(m.srcfile, m.type) + m
                for m in l])
            for l in classes['_conflict'].values()])
        conflicts += '\n\n'
    classes.pop('_conflict')

    for c in classes:
        body += '#\n# [{}]\n#\n'.format(c)
        body += '\n'.join(classes[c])
        body += '\n\n\n'

    if isinstance(OUTPUT, str):
        if os.path.exists(OUTPUT):
            os.rename(OUTPUT, OUTPUT + '.old')
        globals()['OUTPUT'] = open(OUTPUT, 'w')
    print(header + body + conflicts, file=OUTPUT)
    OUTPUT.flush()
    OUTPUT.close()


class HelpArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse.ArgumentParser.error
        #  self.print_usage(_sys.stderr)
        #  self.exit(2, _('%s: error: %s\n') % (self.prog, message))
        message = message + '\n\n' + self.format_help()
        self.exit(2, '%s: error: %s\n' % (self.prog, message))


def main():
    parser = HelpArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=HELP, epilog=EXAMPLE)
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='be more verbose')
    parser.add_argument('dir', nargs='+',
                        help='directory[s] to scan for python source files')
    parser.add_argument('-o', '--output', default=sys.stdout,
                        help='output filename, default stdout')

    args = parser.parse_args()

    globals()['OUTPUT'] = args.output
    globals()['VERBOSE'] = args.verbose

    genrequire(args.dir)

if __name__ == '__main__':
    sys.exit(main())
