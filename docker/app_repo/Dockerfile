FROM phusion/baseimage
MAINTAINER yalon@infinidat.com
ENV HOME /root

RUN /etc/my_init.d/00_regen_ssh_host_keys.sh

RUN apt-get update
RUN apt-get install -y git nginx vsftpd wget python-pip python-dev zlib1g-dev libssl-dev libgnutls-dev
RUN apt-get install -y lsof dnsutils alien createrepo yum rng-tools dpkg-sig
RUN /usr/bin/workaround-docker-2267
RUN /usr/sbin/enable_insecure_key

RUN echo "127.0.0.1 localhost" >> /etc/workaround-docker-2267/hosts
RUN echo "192.168.11.142 pypi01 pypi01.infinidat.com" >> /etc/workaround-docker-2267/hosts
RUN echo "192.168.10.170 infinigit infinigit.infinidat.com" >> /etc/workaround-docker-2267/hosts
RUN echo "172.16.1.74 python.infinidat.com" >> /etc/workaround-docker-2267/hosts

WORKDIR /root
COPY application-repository.deb /root/application-repository.deb
ENV DEBUG_CUSTOM_ACTIONS 1
RUN ["/sbin/my_init", "--", "/usr/bin/dpkg", "-i", "/root/application-repository.deb"]

WORKDIR /
CMD ["/sbin/my_init"]
EXPOSE 8000 8001