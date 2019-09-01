#!/usr/bin/env python
# coding=utf-8
#
# File: EmBCI/embci/utils/_obfuscation.py
# Author: Hankso
# Webpage: https://github.com/hankso
# Time: Mon 04 Mar 2019 17:06:43 CST

'''
This module provides some functions to obfuscate python codes and load
binary files. Some definition of library file:

libpath
    Full path to library filename, e.g.
    `/usr/lib/python3.5/lib-dynload/cmath.cpython-35m-x86_64-linux-gnu.so` and
    `/path/to/embci/processing/libcoef_27_aarch64_linux.so`
libdir
    Directory name of the libpath, `/usr/lib/python3.5/lib-dynload`
libfile
    Base name of the libpath, e.g.
    `cmath.cpython-35m-x86_64-linux-gnu.so` and `libcoef_27_aarch64_linux.so`
libname(modname)
    Bare library name without `lib` prefix and version info: `cmath` & `coef`
'''

import re
_srcfile = re.compile(r'.py[cod]?$')
_libfile = re.compile(r'lib(\w+)\.so(?:\.(\d[0-9.*]))?')
del re

__all__ = ('load_binary', 'obfuscate', 'dump', 'load')


def load_binary_old(filename, module=None, modname='result'):
    '''
    Load and execute obfuscated code. **Deprecated in v0.1.4**

    Examples
    --------
    >>> from embci.utils import load_binary
    >>> mod_coef = load_binary('libcoef.bin', modname='coef')
    >>> mod_coef
    <module 'coef'>
    '''
    import types, marshal, traceback                               # noqa: E401
    with open(_srcfile.sub('.bin', filename), 'rb') as f:
        code = marshal.load(f)
    module = module or types.ModuleType(
        modname, 'Loaded module from obfuscated code source file.')
    try:
        exec(code, module.__dict__)
    except Exception:
        traceback.print_exc()
    return module


def obfuscate_old(filename, code=None, mode='exec'):
    '''
    Obfuscate a module specified by filename or directly code string.
    **Deprecated in v0.1.4**

    Examples
    --------
    >>> obfuscate('coef/libcoef.py')
    >>> with open('coef/__init__.py', 'w') as f:
            f.write(
                "from embci.utils import load_binary\\n"
                "import os, sys\\n"
                "fn = os.path.join(os.path.dirname(__file__), 'libcoef.py')\\n"
                "sys.modules[__name__] = load_binary(fn, modname=__name__)"
            )
    >>> import coef
    '''
    import os, marshal, traceback                                  # noqa: E401
    if code is None:
        with open(_srcfile.sub('.py', filename), 'r') as src:
            code = src.read()
    modname = os.path.splitext(os.path.basename(filename))[0]
    try:
        code = compile(code, '<%s>' % modname, mode)
    except Exception:
        traceback.print_exc()
    with open(_srcfile.sub('.bin', filename), 'wb') as f:
        marshal.dump(code, f)


def libfile_name(modname):
    '''
    cmath.cpython-35m-x86_64-linux-gnu.so
    libcoef_35_x86_64_linux.so
    '''
    import sys, platform                                           # noqa: E401
    return 'lib{name}_{pyver}_{machine}_{system}.{suffix}'.format(
        name = modname,
        # bitness = 64 if sys.maxsize > 2 ** 32 else 32,
        # pyimp = platform.python_implementation().lower(),  # CPython
        pyver = '%d%d' % sys.version_info[:2],
        machine = platform.machine().replace('-', '_') or 'x86_64',
        system = platform.system().lower(),
        suffix = {
            'Linux': 'so',
            'Darwin': 'dylib',
            'Windows': 'dll',
            'Microsoft': 'dll',
        }.get(platform.system(), 'so')
    )


def load_binary(filename=None, modname=None, targets=[]):
    '''
    Protect source code with `Cython` and `gcc compiler` (Added in v0.1.5).
    More details at Cython homepage (http://cython.org/).
    Filename of dynamic link library will be like::
        lib<modname>_<bitness>_<pyversion>_<machine>.<suffix>

    Examples
    --------
    >>> sys.modules['coef'] = load_binary('/path/to/libcoef_35_aarch64.so')
    >>> import coef

    Find suitable lib file automatically.
    >>> mod_coef = load_binary(modname='coef')
    '''
    import os, sys, types, importlib, traceback                    # noqa: E401
    if filename is None:
        if modname is None:
            raise ValueError('modname must be specified when filename is None')
        libfile = libfile_name(modname)
        libdir = os.path.dirname(os.path.abspath(__file__))
        libpath = os.path.join(libdir, libfile)
    else:
        libpath = os.path.abspath(filename)
        libdir, libfile = os.path.split(libpath)
    sys.stderr.write('Using library file `{}`\n'.format(libpath))

    olddir = os.getcwd()
    try:
        os.chdir(libdir)
        module = importlib.import_module(os.path.splitext(libfile)[0])
    except (ImportError, FileNotFoundError):
        sys.stderr.write('Import failed, all functions will be set to `None`')
        sys.stderr.write(traceback.format_exc())
        module = types.ModuleType('empty', 'Loading library failed')
    finally:
        os.chdir(olddir)

    for attr in targets:
        if hasattr(module, attr):
            continue
        sys.stderr.write('Masking attribute `{}` to None.'.format(attr))
        setattr(module, attr, None)
    return module


def obfuscate(filename, modname=None):
    import os, shutil, tempfile, traceback, subprocess             # noqa: E401
    srcpath = os.path.abspath(filename)
    assert os.path.exists(srcpath), 'Source file not exist.'
    libdir, srcfile = os.path.split(srcpath)        # /path/to/asdf.pyx
    libname = os.path.splitext(srcfile)[0]          # asdf
    modname = modname or libname                    # user specified or asdf
    cpyfile = os.path.join(libdir, libname + '.c')  # /path/to/asdf.c
    libfile = libfile_name(modname)                 # libasdf<info>.so
    libpath = os.path.join(libdir, libfile)         # /path/to/libasdf<info>.so

    from Cython.Build import cythonize
    from distutils.extension import Extension
    from distutils.core import setup
    tmpd = tempfile.mkdtemp(dir=libdir)
    try:
        setup(
            # Cythonization
            ext_modules=cythonize([
                Extension(modname, [srcpath]),
            ]),

            # C language compiling, same as command line:
            #   python setup.py --verbose build_ext --debug --force \
            #       --build-lib tmpd --build-temp tmpd
            # TODO: compiled lib not working: no  PyInit function
            script_args=[
                '-v', 'build_ext', '-g', '-f', '-b', tmpd, '-t', tmpd
            ]
        )
    except Exception:
        traceback.print_exc()
    else:
        for fn in os.listdir(tmpd):
            if not fn.startswith(modname):
                continue
            shutil.move(os.path.join(tmpd, fn), libpath)
            print('{} has been updated!'.format(libpath))
            print(subprocess.Popen(
                ['strip', libpath],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            ).communicate()[0])
    finally:
        if os.path.exists(cpyfile):
            os.remove(cpyfile)
        shutil.rmtree(tmpd)


# Aliases
dump = obfuscate
load = load_binary

# THE END
