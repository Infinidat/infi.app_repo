#!/bin/sh

set -e

_apt() {
    echo Setting up...
    distribution=`lsb_release -i | awk '{print tolower($3)}'`
    codename=`lsb_release -c | awk '{print tolower($2)}'`
    echo "deb {{ host_url }}/packages/{{ index_name }}/apt/linux-$distribution $codename main" > /etc/apt/sources.list.d/{{ host }}.{{ index_name }}.list
    echo Installing GPG key...
    curl -s {{ host_url }}/packages/gpg.key | apt-key add -
    echo Fetching package metadata...
    apt-get update > /dev/null 2>&1
}

_yum() {
    echo Setting up...
    distfile=`ls /etc | grep -E "(centos|redhat)-release$" | head -n 1`
    distribution=`cat /etc/$distfile | grep -Eio "centos|red hat|" | head -n 1 | sed -e 's/ //' | awk '{print tolower($1)}'`
    version=`cat /etc/$distfile | grep -Eo "[0-9]+" | head -n 1`
    arch=`uname -m`
    echo "[{{ host }}.{{ index_name }}]
name={{ host }}.{{ index_name }}
baseurl={{ host_url }}/packages/{{ index_name }}/yum/linux-$distribution-$version-$arch/
enabled=1
gpgcheck=1
gpgkey={{ host_url }}/packages/gpg.key" > /etc/yum.repos.d/{{ host }}.{{ index_name }}.repo
    echo Fetching package metadata...
    yum makecache > /dev/null 2>&1
}

_zypper() {
    name={{ host }}.{{ index_name }}
    if [ -f /etc/os-release ]
    then
        version=`cat /etc/os-release | grep -Eo "[0-9]+" | head -n 1`
    else
        version=`cat /etc/SuSE-release | grep -Eo "[0-9]+" | head -n 1`
    fi
    arch=`uname -m`
    url={{ host_url }}/packages/{{ index_name }}/yum/linux-suse-$version-$arch/

    echo Installing GPG key...
    curl -s {{ host_url }}/packages/gpg.key > /tmp/$name.gpg.key
    rpm --import /tmp/$name.gpg.key  > /dev/null 2>&1

    echo Setting up...
    zypper sd $name > /dev/null 2>&1
    zypper sa -t YUM $url $name > /dev/null 2>&1

    echo Fetching package metadata...
    zypper refresh {{ host }}.{{ index_name }} > /dev/null 2>&1
}

# suse
if [ -f /etc/SuSE-release ]
then
    _zypper
    exit 0
fi

# debian-based
if [ -f /etc/debian_version ]
then
    _apt
    exit 0
fi

# redhat-based
if [ -f /etc/redhat-release -o -f /etc/centos-release ]
then
    _yum
    exit 0
fi

echo "OS not supported"
exit 1
