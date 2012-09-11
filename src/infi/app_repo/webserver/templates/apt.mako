#!/bin/sh
echo Setting up...
distribution=`lsb_release -i | awk '{print tolower($2)}'`
codename=`lsb_release -c | awk '{print tolower($2)}'`
echo "deb ftp://${fqdn}/deb/$distribution $codename main" > /etc/apt/sources.list.d/${fqdn}.list
echo Fetching package metadata...
apt-get update > /dev/null 2>&1
