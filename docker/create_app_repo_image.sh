#!/bin/bash
set -e

no_single_deb_package() {
	echo "ERROR: could not find a _single_ application-repository*.deb package"
	exit 1
}

cd `dirname $0`
[[ `ls application-repository-*.deb | wc -l` != 1 ]] && no_single_deb_package

cp application-repository-*.deb app_repo/application-repository.deb

docker build --tag=infi/app_repo --rm=true $* app_repo
