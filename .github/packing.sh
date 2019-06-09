#!/bin/bash
# File: EmBCI-github/.github/packing.sh
# Author: Hankso
# Page: http://github.com/hankso
# Time: Tue 27 Nov 2018 23:51:58 CST
#
# This script will do following jobs:
# - Build binary files
# - Update `embci` package from source
# - Obfuscate source code
# - Build documentation

DIR=${PWD}/`dirname ${BASH_SOURCE[0]}`    # directory of this shell script
REPO_PATH=`dirname ${DIR}`

GIT="git -C ${REPO_PATH}"
LICENSE=EmBCI


#
# Run once to init pyarmor project
#

# pyarmor init --src ${EMBCI_PATH}/embci --type pkg ${DIR}
PYARMOR=${DIR}/pyarmor
# ${PYARMOR} config --name embci --title embci ${DIR}
# wget http://pyarmor.dashingsoft.com/downloads/platforms/orangepi/_pytransform.so -O ${DIR}/_pytransform_aarch64.so


#
#  Build binary files
#

# ${IDF_PATH}/examples/Arduino-core/Arduino_ESP32_Sandbox/0build.sh
# python -m embci.apps.DBS build


#
#  Update package from source directory
#

${GIT} checkout release
rsync -av --del \
    --exclude-from=${DIR}/excludes.txt \
    --exclude-from=${EMBCI_PATH}/.gitignore \
    ${EMBCI_PATH}/ ${REPO_PATH}/

#
#  Obfuscate source code
#

${PYARMOR} build --force -O ${REPO_PATH} ${DIR}
# ${PYARMOR} licenses -e 2020-01-01 ${LICENSE} -O ${DIR}
# cp -v ${DIR}/licenses/${LICENSE}/license.lic ${REPO_PATH}/embci/
cp -v ${DIR}/_pytransform_$(uname -m).so ${REPO_PATH}/embci/_pytransform.so
find ${REPO_PATH}/embci -type f -name "*.pyc" -delete

${GIT} add . && ${GIT} commit -m 'release tag'
# ${GIT} push

BRANCH=release
mkdir -p ${REPO_PATH}/dist && ${GIT} archive --format=tar.gz --prefix=EmBCI/ \
    -v -9 -o ${REPO_PATH}/dist/EmBCI-${BRANCH}.tar.gz ${BRANCH}

#
#  Build documentation
#

# make -C ${REPO_PATH}/docs html
# ${GIT} checkout gh-pages
# # ${GIT} checkout release .gitignore
# rsync -av --del \
#     --exclude-from=${DIR}/excludes.txt \
#     --exclude-from=${EMBCI_PATH}/.gitignore \
#     ${REPO_PATH}/docs/_build/html/ ${REPO_PATH}/
# ${GIT} add . && ${GIT} commit -m 'build documentation for tag'
# # ${GIT} push
