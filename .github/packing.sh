#!/bin/bash
# File: EmBCI-github/.github/packing.sh
# Author: Hankso
# Page: http://github.com/hankso
# Time: Tue 27 Nov 2018 23:51:58 CST
#
# This script will do following jobs:
# - Update `embci` package from source
# - Obfuscate source code
# - Build documentation
# - Build binary files

git checkout release
DIR=`dirname ${BASH_SOURCE[0]}`
BIN=${DIR}/pyarmor
REPO_PATH=`dirname ${DIR}`
LICENSE=EmBCI

#
# Run once to init pyarmor project
#
pyarmor init --src ${EMBCI_PATH}/embci --type pkg ${DIR}
wget http://pyarmor.dashingsoft.com/downloads/platforms/orangepi/_pytransform.so -O ${DIR}/_pytransform.so

#
# Update package from source directory
#
# rm -rf ../embci ../files ../docs ../tests
# cp -av ${EMBCI_PATH}/* ../
rsync -av --del \
    ${EMBCI_PATH}/ \
    ${REPO_PATH}/ \
    --exclude-from=${DIR}/excludes.txt \
    --exclude-from=${EMBCI_PATH}/.gitignore

#
# Obfuscate source code
#
${BIN} config --name embci --title embci ${DIR}
${BIN} build --force -O ${REPO_PATH} ${DIR}
${BIN} licenses -e 2020-01-01 ${LICENSE} -O ${DIR}
cp -v ${DIR}/licenses/${LICENSE}/license.lic ${REPO_PATH}/embci/
if [ `uname -m | grep "arm"` ]; then
    cp ${DIR}/_pytransform.so ${REPO_PATH}/embci/
fi
find ${REPO_PATH}/embci -name "*.pyc" -delete
# find ${REPO_PATH}/embci -name "*.py" -exec python -m py_compile {} \;

#
# Build documentation
#
make -C ${REPO_PATH}/docs html
# git checkout gh-pages
# TMPDIR=`mktemp -d`
# cp -av ${REPO_PATH}/docs/_build/html/* ${TMPDIR}/
# rsync -av --del \
#     ${TMPDIR}/ \
#     ${REPO_PATH}/ \
#     --exclude-from=${DIR}/excludes.txt
#     # --exclude-from=${EMBCI_PATH}/.gitignore
# git add .
# git checkout release
# [ -x $TMPDIR ] && rm -rf TMPDIR


#
# Build binary files
#
${IDF_PATH}/examples/Arduino-core/Arduino_ESP32_Sandbox/0build.sh
