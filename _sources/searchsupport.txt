Search
======

Bargate has EXPERIMENTAL support for simple file name searches since 1.4.1.


Here be dragons!
----------------

The very notion of a client connecting to an SMB server to perform a search
for file names is not a good one - performance is always going to be poor. The 
idea then that the web interface on top should provide searching to a user
connecting over HTTPS - perhaps on the other side of the world - is even more
of a bad idea. Despite this issue bargate does support searching but it is 
disabled by default.

Microsoft has (somewhat) mitigated the performance problem with the 
Windows Search Protocol extension to SMB, however Samba does not have any
support for this so Bargate cannot utilise it. 

If you decide to go ahead and enable searching please read about the 
:ref:`CONFIG_SEARCH_TIMEOUT` option and set it appropriately.

Enable searching
----------------

Set the config option :ref:`CONFIG_SEARCH_ENABLED` to 'True' and restart 
Bargate. Please however read the following section before doing that.

Search timeout
-----------------

Searching on a slow SMB file server will take a long time - probably longer
than the web server timeout. If bargate is still searching for longer than 
the timeout then the web server will kill the connection and return an error
to the browser - probably an unhelpful "504 Gateway Timeout". Worse still if
you're using uwsgi or similar then the process will keep searching behind the 
scenes. It may even be possible then for an attacker to perform a denial of 
service attack by searching a huge, slow file server.

To prevent this Bargate monitors how long the search is taking and stops 
searching when it reaches its own timeout configured via the 
:ref:`CONFIG_SEARCH_TIMEOUT` config option.

You should set this parameter to be less than the timeout the web server is
configured to. If you're using the recommended nginx+uwsgi set up then you 
should set the following nginx parameters like so::

  location @bargate
  {
      include uwsgi_params;
      uwsgi_param HTTPS on;
      uwsgi_pass unix:/var/run/uwsgi.sock;
      uwsgi_read_timeout 120s;
      uwsgi_send_timeout 120s;
  }

You don't need to set these as the default of 60 seconds for both is safest,
but if you want users to be able to search for longer increase the values and
increase :ref:`CONFIG_SEARCH_TIMEOUT` - but remember to keep it less than
the uwsgi_read_timeout and uwsgi_send_timeout options.

