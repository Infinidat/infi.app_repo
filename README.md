Introduction
===========

`infi.app_repo` is a complementary solution to our Python-based applications that are managed using `infi.projector` and its skeleton.

`infi.app_repo` is a comibination of a FTP and HTTP services for the following services:
* APT repository
* YUM reopistory
* Update repository for VMware Studio appliances
* Archive for other distributions (e.g. MSI)

Based on our projects structure, versioning scheme and release process, we can upload distribution to a single incoming directory, and in the background process them and move them to the correct repository.

The HTTP service provides:
* Links for manual download of all packaes stored in the repository
* One-liners for setting up the apt/yum repositories in the matching Linux distributions.

Syncing packages between repositories
-------------------------------------

Before pulling/pushing packages, you will neet to set up the remote target by running:

    bin/app_repo -f <configfile> remote set <fqdn> <user> <password>
    service app_repo_webserver restart

Pulling from other repositories
-------------------------------

Go to http://localhost/pull, authenticate with the `app_repo` username

Pushing to other repositories
-----------------------------

Go to http://localhost/push, authenticate with the `app_repo` username

Installation
============

Running from source
-------------------

The solution is designed and tested only on ubuntu.
You willl need to pre-install the following packages:

* dpkg
* alien
* createrepo
* yum
* vsftpd
* rng-tools
* dpkg-sig
* redis-server

You will also need to install the Python package `infi.projector` by running `easy_install infi.projector`.
After sorting all these requirements, run:

    projector devenv build
    bin/app_repo install

The `install` script does the following:
* writes the configuration file to `/etc/app_repo.conf`
* creates user `app_repo`
* set up `vsftpd` on port 21
* set up the HTTP backend on port 80
* creates a gpg signature for the current user, to be used for signing packages
* users two services, `app_repo_worker` and `app_repo_webserver`

Installing released versions
----------------------------

You can also download and install the released binaries

* `curl http://repo.infinidat.com/apt_source | sh -`
* apt-get install -y application-repository

Deploying a virtual appliance
-----------------------------

`infi.app_repo` is also packages as a VMware virtual appliance (ubuntu based).
You can download it from http://repo.infinidat.com.


Checking out the code
=====================

Run the following:

    easy_install -U infi.projector
    projector devenv build


Running in development mode
===========================

* Create a configuration file:

	bin/app_repo dump defaults --development > config.json

* Change the remote target in `config.json`
* Start the services

	redis-server &
	bin/app_repo -f config.json webserver start &
	bin/app_repo -f config.json worker start &

On platforms other than Ubuntu, the lines above would make the webserver work; you won't be able to really pull packages and process incoming packages because the all RPM/DEB-related utilities does not exist on platforms other than Ubuntu.

On Ubuntu, everything should be ok.


Pulling packages
----------------

Pulling an entire repository can take time, and consume a lot of disk space. Instead, one can just copy the metadata:

	mkdir data
	rm data/metadata.json
	wget http://repo.lab.il.infinidat.com/inventory -O data/metadata.response
	python -c "import json; print json.dumps(json.load(open('data/metadata.response'))['return_value'])" > data/metadata.json
