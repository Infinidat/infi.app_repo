#!/bin/sh

apt() {
    echo Setting up...
    distribution=`lsb_release -i | awk '{print tolower($2)}'`
    codename=`lsb_release -c | awk '{print tolower($2)}'`
    echo "deb ftp://${fqdn}/deb/$distribution $codename main" > /etc/apt/sources.list.d/${fqdn}.list
    echo Installing GPG key...
    curl ftp://${fqdn}/gpg.key | apt-key add -
    echo Fetching package metadata...
    apt-get update > /dev/null 2>&1
}

yum() {
    echo Setting up...
    distribution=`python -c "import platform; print platform.dist()[0].lower()"`
    version=`python -c "import platform; print platform.dist()[1].split('.')[0].lower()"`
    arch=`uname -m`
    echo "[${fqdn}]
    name=${fqdn}
    baseurl=ftp://${fqdn}/rpm/$distribution/$version/$arch/
    enabled=1
    gpgcheck=1
    gpgkey=ftp://${fqdn}/gpg.key" > /etc/yum.repos.d/${fqdn}.repo
    echo Fetching package metadata...
    yum update > /dev/null 2>&1
}

if [ -f "/etc/lsb-release" ]
then
    apt
    exit 0
fi
if [ -f "/etc/redhat-release" ]
then
    yum
    exit 0
echo "OS not supported"
exit 1
