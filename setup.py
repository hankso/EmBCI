from setuptools import setup, find_packages
import os
import glob
import platform

from embci import (__title__, __version__, __author__, __email__,
                   __url__, __doc__, __license__, __keywords__)


with open('requirements.txt') as f:
    requirements = [_.strip() for _ in f.readlines()
                    if not _.startswith('#') and len(_.strip())]

extras = dict(
    project_urls={
        'Documentation': 'https://embci.readthedocs.io/en/latest',
        'Gitbooks': 'https://embci.gitbook.io/doc/',
        'Funding': __url__ + '#Funding',
        'Source Code': __url__,
        'Bug Tracker': os.path.join(__url__, 'issues')
    },
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'embci-webui = embci.webui:main',
        ]
    },
)

if platform.machine() in ['arm', 'aarch64']:
    extras['data_files'] = [
        (os.path.expanduser('~/.embci/'), ['files/service/embci.conf']),
        ('/etc/embci', glob.glob('files/service/*')),
        ('/etc/init.d/', ['files/service/embci']),
    ]

    def enable_autostart():
        import subprocess
        try:
            subprocess.call(['update-rc.d', 'embci', 'enable'])
        except OSError:
            print('No command `update-rc.d`?')
        except subprocess.CalledProcessError:
            print('Enable service `embci` failed.\nYou may want to manually'
                  'enable it with command `update-rc.d embci enable`')
    import atexit
    atexit.register(enable_autostart)


setup(
    name         = __title__,
    version      = __version__,
    url          = __url__,
    author       = __author__,
    author_email = __email__,
    license      = __license__,
    description  = __doc__,
    keywords     = __keywords__,
    packages     = find_packages(
        exclude=['*.tests', 'tests', 'tests.*', '*.tests.*'],
    ),
    **extras
)
