#!/bin/sh

_apt() {
    echo Setting up...
    distribution=`lsb_release -i | awk '{print tolower($3)}'`
    codename=`lsb_release -c | awk '{print tolower($2)}'`
    echo "deb ${host_url}packages/${index_name}/apt/linux-$distribution $codename main" > /etc/apt/sources.list.d/${host}.${index_name}.list
    echo Installing GPG key...
    curl ${host_url}packages/gpg.key | apt-key add -
    echo Fetching package metadata...
    apt-get update > /dev/null 2>&1
}

_yum() {
    echo Setting up...
    version=`cat /etc/$distfile | grep -Eo "[0-9]+" | head -n 1`
    arch=`uname -m`
    echo "[${host}.${index_name}]
name=${host}.${index_name}
baseurl=${host_url}packages/${index_name}/yum/linux-$distribution-$version-$arch/
enabled=1
gpgcheck=1
gpgkey=${host_url}packages/gpg.key" > /etc/yum.repos.d/${host}.${index_name}.repo
    echo Fetching package metadata...
    yum makecache > /dev/null 2>&1
}


# debian-based
if [ -f /etc/debian_version ]
then
    _apt
    exit 0
fi

# redhat-based
distfile=`ls /etc | grep -E "(centos|redhat)-release$" | head -n 1`
distribution=`cat /etc/$distfile | grep -Eio "centos|red hat|" | head -n 1 | sed -e 's/ //' | awk '{print tolower($1)}'`
if [ $distribution = "centos" -o $distribution = "redhat" ]
then
    _yum
    exit 0
fi

echo "OS not supported"
exit 1
