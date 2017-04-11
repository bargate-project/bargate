Known issues
============

Samba bug #11624 - Socket leak on DFS paths
-------------------------------------------

There (was) a bug in Samba / libsmbclient for which the fix has yet to make it 
through to distribution updates. All versions of RHEL are still affected by 
this bug for example.

More details here: https://bugzilla.samba.org/show_bug.cgi?id=11624

If you configure Bargate to let your users connect to shares through DFS paths
then you will almost certainly hit this bug and Bargate will leak connections
leading to hundreds or thousands of zombie connections to port 445 on the 
file server.

The current work around whilst waiting for the bug fix to be made available by
distributions is to simply restart the wsgi server every so often. If you're 
using the recommended nginx+uwsgi approach then add this line to the 
uwsgi.ini configuation file::

   max-worker-lifetime = 900

This will cause uwsgi to restart each worker after 900 seconds (15 minutes).




