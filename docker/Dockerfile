FROM ubuntu:18.04

env LC_ALL C.UTF-8
env LANG C.UTF-8
env DEBIAN_FRONTEND noninteractive
RUN ln -sf /usr/share/zoneinfo/Asia/Jerusalem /etc/localtime

RUN apt-get update && apt-get -y install build-essential tzdata software-properties-common libpq-dev curl git python3-distutils python3-apt python3-all python3-setuptools python3 python3-dev python3-pip python3-wheel python3-stdeb python-all python3-all-dev dpkg alien createrepo yum rng-tools dpkg-sig 
RUN pip3 install infi.projector
RUN pip3 install pypi_switcher
RUN set_index_url https://pypi.infinidat.com/simple
# cp python-v3.8.0.5-linux-ubuntu-bionic-x64.tar.gz "python-v3.8.0.5-linux-ubuntu-Bionic Beaver-x64.tar.gz"      
# projector devenv build --use-isolated-python --force-bootstrap
