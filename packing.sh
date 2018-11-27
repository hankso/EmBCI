#!/bin/bash
# File: EmBCI/dist/dist.sh
# Author: Hankso
# Page: http://github.com/hankso
# Time: Tue 27 Nov 2018 23:51:58 CST

# Run once to init pyarmor project
# pyarmor init --src ${EMBCI_PATH} --type pkg dist/
# rm -rf embci
# cp -a ${EMBCI_PATH} .

cd dist
./pyarmor config --name embci --title embci
./pyarmor build --force --output ../
./pyarmor licenses -e 2019-01-01 -4 10.0.0.1 cheitech-develop
cp licenses/cheitech-develop/license.lic ../embci/

cd ../
find embci -name "*.pyc" -delete
# find embci -name "*.py" -exec python -m py_compile {} \;
wget http://pyarmor.dashingsoft.com/downloads/platforms/orangepi/_pytransform.so -O embci/_pytransform.so
