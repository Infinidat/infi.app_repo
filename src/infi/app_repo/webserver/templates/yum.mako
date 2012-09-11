#!/bin/sh
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
