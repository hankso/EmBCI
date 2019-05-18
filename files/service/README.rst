EmBCI Linux Service
-------------------

EmBCI Tasks
===========

The scripts in this directory whos names begin with a special
alphabet will be executed when starting/reloading/stopping
service embci.

+----------+------------------------------+
| Alphabet | Meanings                     |
+==========+==============================+
| E        | Essential tasks              |
+----------+------------------------------+
| O        | Optionally tasks             |
+----------+------------------------------+
| A        | Applications                 |
+----------+------------------------------+
| D        | Disabled scripts             |
+----------+------------------------------+
| K        | Executed when stopping embci |
+----------+------------------------------+
| R        | Reload scripts               |
+----------+------------------------------+

Usage
=====

To enable a script/task in embci service, rename the script so
that it begins with corresponding alphabet. Filenames starts
with other alphabets will be ignored.

Rules
=====
Each script must apply:

- Scripts must be executable.
- Scripts must start with a :code:`shebang` mark, such as **#!/bin/sh** and **#!/bin/env python**.
- Filenames are case-sensetive, i.g. :code:`E01xxx` is essential but :code:`e01xxx` will be ignored.
