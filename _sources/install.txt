Installation
===================================

Requirements
-------------------

- Linux

- Python 2.6 or 2.7 (Python 3 is not yet supported)

- A WSGI capable web server (e.g. nginx+uwsgi or apache+mod_wsgi)

- Python modules:

  - Flask
  - pysmbc
  - pycrypto
  - Pillow
  - ldap (optional)
  - kerberos (optional)
  - redis-py (optional)
  - onetimepass (optional)
  - pyqrcode (optional)

- libsmbclient

- Redis (optional)

Install system packages
-----------------------

On Red Hat Enterprise Linux or Fedora::

  yum install python-pip redis git

You will want to enable the redis server on RHEL6::

  chkconfig redis on
  service redis start

...or on RHEL7::

  systemctl enable redis
  systemctl start redis

On Debian or Ubuntu::

  apt-get install python-pip redis-server git

Install development packages
----------------------------

To install the pip modules you will need to install some development packages - these can be removed once you've installed the python packages if you desire.

On Red Hat Enterprise Linux or Fedora::

  yum install gcc python-devel libsmbclient-devel openldap-devel zlib-devel libjpeg-turbo-devel libtiff-devel freetype-devel libwebp-devel lcms2-devel krb5-devel

On Debian or Ubuntu::

  apt-get install build-essential python-dev libsmbclient-dev samba-dev zlib1g libopenjpeg-dev libopenjpeg2 libtiff5-dev libfreetype6-dev libwebp-dev liblcms2-dev libldap2-dev libsasl2-dev libkrb5-dev

Install python packages
-----------------------

Install the packages with pip::

  pip install Flask pysmbc pycrypto Pillow redis python-ldap kerberos onetimepass pyqrcode

Install bargate 
---------------

Choose a directory to install bargate to. This guide assumes /opt/bargate::

  cd /opt/
  git clone https://github.com/divad/bargate.git

You will want to choose a version to run - to do this you can use git branches.
The latest stable branch is 'v1.4'. Switch to that branch to ensure that
running 'git pull' won't update you to a major release::

  cd /opt/bargate
  git checkout v1.4

Next steps
---------------

- Configure bargate. See :doc:`config` for more information.
- Deploy bargate with a web server. See :doc:`deploy` on how to do that.
