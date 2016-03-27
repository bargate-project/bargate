Shares configuration
====================

Bargate should be configured with a series of server and share
combinations to present to the users, otherwise only the 'custom' (i.e.
enter manually) share system is available. These shares are configured
in the shares config file, usually /etc/bargate/shares.conf (this path
is configured via the :ref:`CONFIG_SHARES_CONFIG` parameter).

Shares syntax
-------------

The shares config file uses the INI format (specifically, Python's
`ConfigParser
format <https://docs.python.org/2/library/configparser.html>`__). The
file is broken up into sections, each section representing an SMB share.
The syntax for each section is as follows:

.. code:: ini

    [section_name]
    url = /<url_name>
    path = smb://server.domain.tld/share/
    menu = <menu_name>
    display = <display_name>

-  ``[section_name]`` must be a unique name for this smb share, however
   it is never displayed to the end user.
-  ``url`` is the url displayed or entered by the user to access this
   share, e.g. /yournamehere
-  ``path`` is the SMB URI of the share on the remote server to connect
   to
-  ``menu`` is the name of the menu which should be marked as active
   when the share is being browsed by the user
-  ``display`` is what bargate will display as the name of the share

Variable insertion
------------------

Sometimes you want to use the username of the user using the share as
part of the SMB server path. Bargate supports this by dynamically at
runtime replacing variables with the username or, if using LDAP home dir
support, the home directory of the user. These variables are:

-  ``%USERNAME%`` - resolves to the username
-  ``%USER%`` - resolves to the username
-  ``%LDAP_HOMEDIR%`` - resolves to the LDAP home directory of the user,
   if present

See :ref:`CONFIG_SECTION_LDAP_HOME_DIR` for LDAP home directory support

Examples
--------

.. code:: ini

    [webfiles]
    url = /webfiles
    path = smb://webfiles.soton.ac.uk/%USERNAME%/
    menu = home
    display = My Website

.. code:: ini

    [dfs]
    url = /dfs
    path = smb://soton.ac.uk/
    menu = dfsroot
    display = DFS Root

.. code:: ini

    [homedir]
    url = /home
    path = %LDAP_HOMEDIR%
    menu = homedir
    display = My Files

