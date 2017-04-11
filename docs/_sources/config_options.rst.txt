Configuration options
=====================

Required options
----------------

.. _CONFIG_SECRET_KEY:

SECRET\_KEY
~~~~~~~~~~~

-  **Required**: Yes
-  **Expected value**: Variable length quoted String
-  **Type**: Flask config option
-  **Default**: Empty string

This is the key used to sign client-side cookies. This key must never be
revealed to anybody. If you are using multiple Bargate instances behind
a round-robin load balancer than this key must match on all instances so
that either server will accept the client side cookie.

The longer the key the better (like any password).

.. _CONFIG_ENCRYPT_KEY:

ENCRYPT\_KEY
~~~~~~~~~~~~

-  **Required**: Yes
-  **Expected value**: 32-character quoted String
-  **Type**: Bargate specific config option
-  **Default**: Empty string

This is the key used to encrypt the user's password. This key is even
more important than SECRET\_KEY and must never be revealed to anybody.
If you are using multiple Bargate instances behind a round-robin load
balancer than this key must match on all instances so that either server
will be able to decrypt the user's password for use on the SMB server.

.. _CONFIG_DISABLE_APP:

DISABLE\_APP
~~~~~~~~~~~~

-  **Required**: Yes
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True

This config option enables or disables Bargate. This defaults to true to
make sure a site-specific config file has been created.

Core options
------------

SMB\_WORKGROUP
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Quoted string
-  **Type**: Bargate specific config option
-  **Default**: 'MSHOME'

The legacy domain name or workgroup to use when authenticating to an SMB
server.

When connecting to a SMB/CIFS server you send the username, password and
"workgroup" (which is today called the 'legacy domain name' when joined
to Active Directory). This is often called the "NetBIOS domain name" as
well. Set this parameter to your domain's "legacy" domain name.

AUTH\_TYPE
~~~~~~~~~~

-  **Required**: No
-  **Expected value**: "LDAP" or "Kerberos"
-  **Type**: Bargate specific config option
-  **Default**: "LDAP"

This option determines how to authenticate users. Kerberos is not
currently recommended due to a lack of KDC verification in Apple's
pyKerberos.

THEME\_DEFAULT
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'lumen'

The name of the theme to use by default. Users can change this if REDIS is enabled.

LAYOUT\_DEFAULT
~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: 'grid' or 'list'
-  **Type**: Bargate specific config option
-  **Default**: 'grid'
-  **Since**: 1.4

The default layout mode to use, either 'grid' or 'list'. Users can change this if REDIS is enabled.

PREFERRED\_URL\_SCHEME
~~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: 'http' or 'https'
-  **Type**: Flask option
-  **Default**: 'https'

The URL scheme that should be used for URL generation if no URL scheme
is available. This defaults to https.

REMEMBER\_ME\_ENABLED
~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate option
-  **Default**: True

If enabled then users can choose the "Keep me logged in" option at logon
time and the session is set to be 'permanent', as defined by the
permanent session lifetime option (See below). Disabling this
significantly improves security since it reduces the likelihood an
attack can steal passwords from the end user's browser (although if this
did happen they are still encrypted with AES).

PERMANENT\_SESSION\_LIFETIME
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: 'http' or 'https'
-  **Type**: Flask option
-  **Default**: timedelta(days=7)

The lifetime of a permanent session as as an integer representing
seconds or as a Python datetime.timedelta object.


.. _CONFIG_SHARES_CONFIG:

SHARES\_CONFIG
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: '/etc/bargate/shares.conf'

The location of the SMB shares config file. See :doc:`shares` for more information.

SHARES\_DEFAULT
~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'personal'

The default SMB share to connect to when a user logs in.

.. _CONFIG_LOCAL_TEMPLATE_DIR:

LOCAL\_TEMPLATE\_DIR
~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: False or a String
-  **Type**: Bargate specific config option
-  **Default**: False

Bargate templates can be overridden to allow you to customise various parts
of bargate - or all of bargate. This option defines a local directory where
templates should be loaded from before loading them from inside bargate.

See :doc:`templates` for more information.

.. _CONFIG_LOCAL_STATIC_DIR:

LOCAL\_STATIC\_DIR
~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: False or a String
-  **Type**: Bargate specific config option
-  **Default**: False
-  **Since**: 1.5

Set a directory where local static files reside. This is useful for customising
bargate with your own favicon, images, javascript or CSS. If a 'favicon.ico' 
file resides within this directory it will be automatically used as the favicon
for bargate.

To use other files in your local static directory you will need to reference 
them using the local_static function in templates (which themselves should
resides in LOCAL_TEMPLATE_DIR). Reference the files like so::

  {{ url_for('local_static', filename='logo.png') }}

See :doc:`templates` for more information.

APP\_DISPLAY\_NAME
~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'Filestore Web Access'

The application wide display name.

APP\_DISPLAY\_NAME\_SHORT
~~~~~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'Filestore Web Access'

The shortened version of the application wide display name.

LOGIN\_IMAGE\_RANDOM\_MAX
~~~~~~~~~~~~~~~~~~~~~~~~~

**This config option is deprecated and REMOVED in 1.4**

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: 17
-  **Removed**: 1.4

The default login page (which you don't have to use) sets a background
image from a pool of images based on a random number. This option sets
the upper bounds on that random number.

This option has been removed in version 1.4 and is replaced by Jinja template
filters, e.g::

  {{range(1,17)|random}}

IMAGE\_PREVIEW
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True
-  **Since**: 1.3.3

Whether to enable image previews when users click entries in a directory
listing

IMAGE\_PREVIEW\_MAX\_SIZE
~~~~~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: 30\ *1024*\ 1024
-  **Since**: 1.3.3

The maximum file size, in bytes, of image files that will be previewed

File uploads
------------

.. _CONFIG_MAX_CONTENT_LENGTH:

MAX\_CONTENT\_LENGTH
~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: 268435456 (256MB)

This parameter sets the maximum file upload size in bytes. Since the
config file is a Python file you can write "256 \* 1024 \* 1024" to set
it to 256MB to make future changes easier.

BANNED\_EXTENSIONS
~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: set([ "ade", "adp", "bat", "chm", "cmd", "com", "cpl",
   "exe", "hta", "ins", "isp", "jse", "lib", "mde", "msc", "msp", "mst",
   "pif", "scr", "sct", "shb", "sys", "vb", "vbe", "vbs", "vxd", "wsc",
   "wsf", "wsh" ])

This parameter sets the banned file extensions that Bargate should
reject on file upload. This is intended to help prevent executable files
being uploaded. If you want to disable this set the value to "set()".
This feature exists just to help protect Windows users.

LDAP Auth
---------

LDAP\_URI
~~~~~~~~~

-  **Required**: No (Yes for LDAP support)
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'ldaps://localhost.localdomain'

The LDAP server to connect to. This is a URI, so it should start with
ldap:// or ldaps:// and can end in a port if required.

LDAP\_SEARCH\_BASE
~~~~~~~~~~~~~~~~~~

-  **Required**: No (Yes for LDAP support)
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: ''

The LDAP base OU where searches for users should take place.

LDAP\_USER\_ATTRIBUTE
~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'sAMAccountName'

The username attribute on each user object within the directory.

LDAP\_ANON\_BIND
~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True

When searching for users in the LDAP server you need to bind to search.
By default this option is set to True, which means Bargate will bind
anonymously. If your LDAP server needs you to bind with a
username/password set this to false and fill in LDAP\_BIND\_USER and
LDAP\_BIND\_PW.

LDAP\_BIND\_USER
~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True

The username to bind with if needed for searching.

LDAP\_BIND\_PW
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True

The password to bind with if needed for searching.

.. _CONFIG_SECTION_LDAP_HOME_DIR:

LDAP Home directory support
---------------------------

LDAP\_HOMEDIR
~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: False

Should bargate try to lookup the user's 'home directory' from LDAP.

LDAP\_HOME\_ATTRIBUTE
~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'homeDirectory'

What LDAP attribute holds the user's home directory.

LDAP\_HOMEDIR\_IS\_UNC
~~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True

By default Bargate assumes that the LDAP home dir attribute contains a
non-standard UNC (Windows) path. Bargate converts the UNC path into a
standards compliant URI instead. If your LDAP server stores the home
directory attribute in the correct 'smb://server/share/folder' format
then set this to False.

Kerberos authentication
-----------------------

KRB5\_DOMAIN
~~~~~~~~~~~~

-  **Required**: No (Yes if using Kerberos authentication)
-  **Expected value**: Quoted string
-  **Type**: Bargate specific config option
-  **Default**: 'localhost.localdomain'

The Kerberos domain name. If you use Active Directory this is the
"domain name" of Active Directory, not the NT domain name.

**Do not use kerberos authentication due to CVE-2015-3206**

KRB5\_SERVICE
~~~~~~~~~~~~~

-  **Required**: No (Yes if using Kerberos authentication)
-  **Expected value**: Quoted string
-  **Type**: Bargate specific config option
-  **Default**: 'krbtgt/localdomain'

**Do not use kerberos authentication due to CVE-2015-3206**

When using Kerberos authentication you need to set the "service
principal" which usually is 'krbtgt/domain-name'. For example for
soton.ac.uk the krb5 service is 'krbtgt/soton.ac.uk'. Future versions of
Bargate will attempt to build this for you if KRB5\_SERVICE is not set
but KRB5\_DOMAIN is.

SMB authentication
------------------

SMB\_AUTH\_URI
~~~~~~~~~~~~~~

-  **Required**: No (Yes if using SMB authentication)
-  **Expected value**: Quoted string
-  **Type**: Bargate specific config option
-  **Default**: 'smb://yourdomain.tld/NETLOGON/'

SMB authentication works by connecting to an SMB URI (address) and
attempting to list the contents of a share. Thus this option should be
the address of an SMB server and share which you must authenticate to
access. Usually this can be something like
'smb://server.domain/NETLOGON' or whatever share you want to use. When
setting this up please make sure to test that invalid usernames and
passwords are not accepted by the back end server.

This feature is EXPERIMENTAL and has not received extensive testing. It
is designed for environments where LDAP and Kerberos are not available
but the SMB server is.

Two factor authentication
-------------------------

**Please note:** Two factor authentication support is considered EXPERIMENTAL.

TOTP\_ENABLED
~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: False

This option enables or disables TOTP (time based one time password)
support. This implements RFC6238 two factor authentication. TOTP support
requires REDIS to be enabled.

TOTP\_IDENT
~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Quoted string
-  **Type**: Bargate specific config option
-  **Default**: 'bargate'

When using two factor authentication the application generates TOTP URLs
to give to the end user. Within this URL is an 'identity' which is
usually shown within the authenticator smartphone application to enable
the user to identify what that entry is for. This configuration option
determines what the ident is. You can safely change this ident at any
time since it is only used for the initial set up.

Logging
-------

FILE\_LOG
~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True

Should bargate log information to files? This option exists in case you
don't want to enable file logging.

LOG\_DIR
~~~~~~~~

-  **Required**: No
-  **Expected value**: Quoted string
-  **Type**: Bargate specific config option
-  **Default**: '/tmp'

The directory to store bargate logs in.

LOG\_FILE
~~~~~~~~~

-  **Required**: No
-  **Expected value**: Quoted string
-  **Type**: Bargate specific config option
-  **Default**: 'bargate.log'

The file name of the log file that bargate should store logs in,
combined with LOG\_DIR to create a full path to the file.

LOG\_FILE\_MAX\_SIZE
~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: 1048576 (1MB)

The maximum size of the log file before bargate rotates the log file and
creates a new one. Defaults to 1MB. Since the config file is a Python
file you can write "1 \* 1024 \* 1024" to set it to 1MB to make future
changes easier to write.

LOG\_FILE\_MAX\_FILES
~~~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: 10

The maximum size number of old rotated log files to keep. Files beyond
this limit will be deleted as new logs are rotated.

E-mail alerts
-------------

EMAIL\_ALERTS
~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: False

Enable or disable e-mail alerts when severe/critical errors are
encountered.

ADMINS
~~~~~~

-  **Required**: No
-  **Expected value**: List of strings
-  **Type**: Bargate specific config option
-  **Default**: ['root']

A list of e-mail addresses to send e-mail alerts to if enabled.

SMTP\_SERVER
~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Strings
-  **Type**: Bargate specific config option
-  **Default**: localhost

The SMTP server to send e-mails via.

EMAIL\_FROM
~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: root

If e-mail alerts are enabled then who should they appear to be sent
from.

EMAIL\_SUBJECT
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'Bargate Runtime Error'

If e-mail alerts are enabled then what should the subject of the e-mail
be

REDIS
-----

REDIS\_ENABLED
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: True

Should Redis be used for storing user preferences and data?

REDIS\_HOST
~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: 'localhost'

What is the hostname of the Redis server. In almost all cases this
should be 'localhost'.

REDIS\_PORT
~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: 6379

What is the port of the Redis server. In almost all cases this should be
left as default.

SID Lookups (winbind lookups)
-----------------------------

WBINFO\_LOOKUP
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: False
-  **Since**: 1.4

When enabled bargate will use winbind to resolve SIDs (security identifiers) to
usernames and group names to present to the user. This enables bargate to tell the
user which user and group a file belongs to.

Turning this option requires that winbind is installed and running.

WBINFO\_BINARY
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: String
-  **Type**: Bargate specific config option
-  **Default**: /usr/bin/wbinfo
-  **Since**: 1.4

The location on the local system of the 'wbinfo' binary which is used by bargate
to resolve SIDs to names.

Debugging
---------

DEBUG
~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Flask config option
-  **Default**: False

Set to True to enable verbose debug logging

DEBUG\_TOOLBAR
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: False

Set to True to enable the Flask Debug Toolbar. **DO NOT USE THIS IN
PRODUCTION.** This exposes SECRET\_KEY and ENCRYPT\_KEY which should
only be known by the application. The Flask debug toolbar is documented
here: https://flask-debugtoolbar.readthedocs.org/en/latest/

This option requires you install Flask-DebugToolbar::

  pip install Flask-DebugToolbar

DEBUG\_FULL\_ERRORS
~~~~~~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: False

When errors are generated from the SMB server most of the time Bargate
redirects the user to the parent folder and shows a simplified error
message, but this can hide the real error. To prevent this behaviour set
DEBUG\_FULL\_ERRORS to True and all errors will print a full error stack
trace.

.. _CONFIG_SECTION_SEARCH:

Search support
-----------------------------

.. _CONFIG_SEARCH_ENABLED:

SEARCH_ENABLED
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: True or False
-  **Type**: Bargate specific config option
-  **Default**: False
-  **Since**: 1.4.1

Whether to enable the search support in Bargate. See: :doc:`searchsupport` for more
information.

.. _CONFIG_SEARCH_TIMEOUT:

SEARCH_TIMEOUT
~~~~~~~~~~~~~~

-  **Required**: No
-  **Expected value**: Integer
-  **Type**: Bargate specific config option
-  **Default**: 60
-  **Since**: 1.4.1

The number of seconds before Bargate should stop searching and return what it
has found to the user. This is required because HTTP connections cannot run
forever - most web servers will timeout a process taking too long to return
data to the user - usually around 60 seconds. You should set this to be lower
than the setting the web server uses. If you're using nginx and uwsgi set this
to be lower than 'uwsgi_read_timeout' and 'uwsgi_send_timeout'.
