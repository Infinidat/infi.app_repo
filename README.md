Introduction
===========

`infi.app_repo` is a complementary solution to our Python-based applications that are managed using `infi.projector` and its skeleton.

`infi.app_repo` is a comibination of a FTP and HTTP services for the following services:
* APT repository
* YUM reopistory
* Update repository for VMware Studio appliances
* Pretty HTML index
* Archive for other distributions (e.g. MSI)

Installation
============

Running from source
-------------------

The production, the solution is designed and tested only on ubuntu.
For testing purposes, the project can run on other Linux distributions and OSX versions, with mocks where needed.

On Ubuntu, you willl need to pre-install the following packages:

* dpkg
* alien
* createrepo
* yum
* rng-tools
* dpkg-sig
* curl

You will also need to install the Python package `infi.projector` by running `easy_install infi.projector`.
After sorting all these requirements, run:

    projector devenv build

Setting up the repository
-------------------------

TBD

Running the services
====================

TBD

Python 3 Support
================
Python 3 support is experimental and not fully tested.


Local Development
==================

Build by running: (this takes a while)

```
make build
```

Start the services by running:

```
make testserver
```

Process a file by running:

```
make process_file FILE=<path to file>
```

Stop the services by running:

```
make stop_testserver
```

To run any command:

```
make run CMD=<your command>
```

e.g to run python shell:

```
make run CMD=bin/python
```
