#!/bin/bash
set -e

if [[ "$1" = "-h" || "$1" = "--help" ]]; then
	echo "usage: $0 [--ignore-dirty-repo]"
	exit 1
fi

dirty_error() {
	echo "ERROR: parent git repository is dirty, please clean and/or commit all changes."
	exit 1
}

cd `dirname $0`

# Check that the git repo is clean, otherwise fail.
if [[ "$1" != "--ignore-dirty-repo" ]]; then
	[[ `(cd .. ; git status --porcelain 2>/dev/null | wc -l)` != '0' ]] && dirty_error
fi

[[ -d build_env/app_repo_pristine ]] && ( echo "Deleting previous app_repo_pristine."; rm -rf build_env/app_repo_pristine )

echo "Cloning parent repo into app_repo_pristine." && ( cd build_env ; git clone -q ../.. app_repo_pristine )

echo "Building app_repo build container that will build the deb package."
docker build --tag=infi/app_repo_build --rm=true build_env

echo "Identifying deb package name."
PACKAGE_NAME=`sudo docker run --rm=true infi/app_repo_build /bin/ls /root/app_repo/parts | grep .deb`
echo "Package name: $PACKAGE_NAME"

echo "Copying package from container to host."
CID=`sudo docker run -d infi/app_repo_build '/bin/echo'`
docker cp $CID:/root/app_repo/parts/$PACKAGE_NAME .
docker rm $CID
chown $USER.$GID $PACKAGE_NAME
