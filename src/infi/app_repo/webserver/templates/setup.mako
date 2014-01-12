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

distfile=`ls /etc | grep -E "(debian|centos|redhat)[-_](release|version)$" | head -n 1`
distribution=`echo $distfile | grep -Eo "[a-z]+" | head -n 1`
if [ $distribution = "debian" ]
then
    _apt
    exit 0
fi
if [ $distribution = "centos" -o $distribution = "redhat" ]
then
    _yum
    exit 0
fi
echo "OS not supported"
exit 1
