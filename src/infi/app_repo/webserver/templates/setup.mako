#!/bin/sh

_apt() {
    echo Setting up...
    distribution=`lsb_release -i | awk '{print tolower($3)}'`
    codename=`lsb_release -c | awk '{print tolower($2)}'`
    echo "deb ftp://${fqdn}/deb/$distribution $codename main" > /etc/apt/sources.list.d/${fqdn}.list
    echo Installing GPG key...
    curl ftp://${fqdn}/gpg.key | apt-key add -
    echo Fetching package metadata...
    apt-get update > /dev/null 2>&1
}

_yum() {
    echo Setting up...
    distfile=`ls /etc | grep -E "(\w+)[-_](release|version)$" | head -n 1`
    distribution=`echo $distfile | grep -Eo "\w+" | head -n 1`
    version=`cat /etc/$distfile | grep -Eo "[0-9]+" | head -n 1`
    arch=`uname -m`
    echo "[${fqdn}]
name=${fqdn}
baseurl=ftp://${fqdn}/rpm/$distribution/$version/$arch/
enabled=1
gpgcheck=1
gpgkey=ftp://${fqdn}/gpg.key" > /etc/yum.repos.d/${fqdn}.repo
    echo Fetching package metadata...
    yum makecache > /dev/null 2>&1
}

if [ -f "/etc/lsb-release" ]
then
    _apt
    exit 0
fi
if [ -f "/etc/redhat-release" ]
then
    _yum
    exit 0
fi
echo "OS not supported"
exit 1
