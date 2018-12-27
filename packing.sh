#!/bin/bash
# File: EmBCI/dist/dist.sh
# Author: Hankso
# Page: http://github.com/hankso
# Time: Tue 27 Nov 2018 23:51:58 CST
#
# This script will update `embci` package from source
#

# Run once to init pyarmor project
# pyarmor init --src ${EMBCI_PATH} --type pkg dist/
# wget http://pyarmor.dashingsoft.com/downloads/platforms/orangepi/_pytransform.so -O dist/_pytransform.so

rm -rf embci
cp -a ${EMBCI_PATH}/embci . 2>/dev/null

# obfuscate source code
cd dist
./pyarmor config --name embci --title embci
./pyarmor build --force --output ../
./pyarmor licenses -e 2019-01-01 cheitech-develop
cp licenses/cheitech-develop/license.lic ../embci/
cp _pytransform.so ../embci/
cd ../

find embci -name "*.pyc" -delete
# find embci -name "*.py" -exec python -m py_compile {} \;
