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
