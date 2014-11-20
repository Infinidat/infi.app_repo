FROM phusion/baseimage
MAINTAINER yalon@infinidat.com
ENV HOME /root

RUN /etc/my_init.d/00_regen_ssh_host_keys.sh

CMD ["/sbin/my_init"]

RUN apt-get update
RUN apt-get install -y git nginx vsftpd python-pip python-dev zlib1g-dev libssl-dev libgnutls-dev
RUN apt-get install -y dnsutils alien createrepo yum rng-tools dpkg-sig
RUN /usr/bin/workaround-docker-2267

RUN echo "127.0.0.1 localhost" >> /etc/workaround-docker-2267/hosts
RUN echo "192.168.11.142 pypi01 pypi01.infinidat.com" >> /etc/workaround-docker-2267/hosts
RUN echo "192.168.10.170 infinigit infinigit.infinidat.com" >> /etc/workaround-docker-2267/hosts
RUN echo "172.16.1.74 python.infinidat.com" >> /etc/workaround-docker-2267/hosts

# Set up buildout/easy_install and infi.projector
RUN mkdir ~/.buildout
RUN bash -c 'printf "[buildout]\nindex = http://pypi01.infinidat.com/simple/\n" > ~/.buildout/default.cfg'
RUN bash -c 'printf "[easy_install]\nindex-url = http://pypi01.infinidat.com/simple/\n" > ~/.pydistutils.cfg'
RUN easy_install infi.projector
RUN easy_install infi.vendata.projector.plugins.gitorious

WORKDIR /root
COPY app_repo_pristine /root/app_repo
WORKDIR /root/app_repo
RUN git clean -fdx
RUN projector devenv build --use-isolated-python
RUN projector devenv pack
