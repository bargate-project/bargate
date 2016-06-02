Deployment
==========

You have several options when choosing how to deploy bargate. You are strongly 
recommended to use the combination of uWSGI and nginx - but you can also deploy
with mod_wsgi and apache.

nginx and uWSGI
-------------------

This is the recommended option for deploying bargate, it offers the best 
performance and a range of options not available with other choices.

Install uWSGI and nginx
~~~~~~~~~~~~~~~~~~~~~~~

First we must install uWSGI and nginx. For uWSGI it is probably best to install 
this via 'pip' on any Linux platform so you get the latest version::

  pip install uWSGI

If you can prefer you can install it via your distributions package manager.

For nginx you will need to use your package manager::

  yum install nginx

or::

  apt-get install nginx

Configure uWSGI
~~~~~~~~~~~~~~~

uWSGI can be configured in multiple ways but you should probably use the 'ini'
format. A sample configuration file for bargate is below::

  [uwsgi]
  socket = /var/run/uwsgi.sock
  master = true
  processes = 10
  module=bargate:app
  uid = nobody
  gid = nobody
  logto = /var/log/uwsgi.log
  python-path = /opt/
  chmod-socket = 700
  chown-socket = nginx
  protocol = uwsgi
  pidfile = /var/run/uwsgi.pid

You could place this in /etc/bargate/uwsgi.ini or place it in whatever location
suits your environment. All of the paths above can be changed, and the user
should probably not be left as 'nobody' - pick a user or create a new one such
as 'bargate'.

The socket - the way uWSGI and nginx communicate - needs to be set so that 
nginx can communicate with it - and nothing else - so in the above example
the socket is set to be owned by 'nginx' and permissions set to limit access
to only the owner.

Whatever user/group you decide to set in the uid/gid options above must be able
to read the config files for bargate. See :doc:`config` for details about the 
bargate configuration file.

Run uWSGI as a service (systemd)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You now need to configure uWSGI to run as a service. On systemd based platforms 
(e.g. RHEL7+, Debian 8+, Fedora 15+, Ubuntu 15.04+) you should create a service 
unit file. Create the file in /etc/systemd/system/bargate.service with the 
following contents::

  [Unit]
  Description=bargate web filestore server
  After=network.target

  [Service]
  ExecStart=/usr/bin/uwsgi /etc/bargate/uwsgi.ini --die-on-term
  Restart=always

  [Install]
  WantedBy=multi-user.target

You should then ask systemd to reload::

  systemctl daemon-reload

And then enable and start the service::

  systemctl enable bargate
  systemctl start bargate

Run uWSGI as a service (upstart)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TBD

Connect nginx to uWSGI
~~~~~~~~~~~~~~~~~~~~~~

The final step is to configure nginx to speak to uWSGI. Configuring nginx itself
is beyond the scope of this document, but you'll need a 'server' block in your
nginx configuration and within that add these lines to your nginx.conf::

  client_max_body_size 257M;

  location /static/
  {
      root /opt/bargate/;
  }

  location / { try_files $uri @bargate; }
  location @bargate
  {
      include uwsgi_params;
      uwsgi_param HTTPS on;
      uwsgi_pass unix:/var/run/uwsgi.sock;
  }

The above example assumes HTTPS - which you were going to use anyway, right?

You should set the 'client_max_body_size' option to be at least the same 
size as you tell Bargate to allow via the :ref:`CONFIG_MAX_CONTENT_LENGTH` 
configuration option.

If you intend on using search you may wish to add the 'uwsgi_read_timeout'
and 'uwsgi_send_timeout' options. See :doc:`searchsupport` for more information 
on how to set this up.

Enable and start nginx
~~~~~~~~~~~~~~~~~~~~~~~

You'll want to enable and start nginx (on systemd systems)::

  systemctl enable nginx
  systemctl start nginx

On RHEL6::

  chkconfig nginx on
  service nginx start

apache and mod_wsgi
-------------------
