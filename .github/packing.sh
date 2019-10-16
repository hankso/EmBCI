#!/bin/bash
# File: EmBCI/.github/packing.sh
# Authors: Hank <hankso1106@gmail.com>
# Create: 2018-11-27 23:51:58
#
# This script will do following jobs:
# - Build binary files
# //- Update `embci` package from source
# //- Obfuscate source code
# - Build documentation

DIR=${PWD}/`dirname ${BASH_SOURCE[0]}`    # directory of this shell script
REPO_PATH=`dirname ${DIR}`

GIT="git -C ${REPO_PATH}"

#
#  Build binary files
#

# ${IDF_PATH}/examples/Arduino-core/Arduino_ESP32_Sandbox/0build.sh
# python -m embci.apps.DBS build

#
#  Build documentation
#

$GIT checkout webserver
make -C ${REPO_PATH}/docs html
$GIT checkout gh-pages
# $GIT checkout release .gitignore
# rsync -av --del \
#     --exclude-from=${DIR}/excludes.txt \
#     --exclude-from=${REPO_PATH}/.gitignore \
#     ${REPO_PATH}/docs/_build/html/ ${REPO_PATH}/
cp -av ${REPO_PATH}/docs/_build/html/. ${REPO_PATH}/
$GIT add . && $GIT commit -m "build documentation for `$GIT tag | tail -n1`"
$GIT checkout webserver
# ${GIT} push
