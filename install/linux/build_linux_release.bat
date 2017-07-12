#!/bin/bash

RELEASE_VERSION=${1}
if [ $# -eq 0 ] ; then
        MAJOR=$(git describe | cut -d \- -f 1 | cut -d . -f 1)
        MINOR=$(git describe | cut -d \- -f 1 | cut -d . -f 2)
        BUGFIX=$(git describe | cut -d \- -f 1 | cut -d . -f 3)
        VERSION=$(git describe --exact-match HEAD 2>/dev/null)
        HASH=$(git rev-parse --short HEAD)
        
        if [ ! -z "$VERSION" ]; then
                RELEASE_VERSION=${VERSION}
        else
                RELEASE_VERSION=${MAJOR}.${MINOR}.${BUGFIX}_${HASH}
        fi
fi

rm -rf dist build racecapture_linux_*.tgz

pyinstaller --clean -y racecapture_linux.spec

# pyinstaller includes unneeded files from share
# improve the pyinstaller script and this can be removed
rm -rf ./dist/racecapture/share

#package into tar file
tar czvfC racecapture_linux_${RELEASE_VERSION}.tgz dist racecapture
