Configuration
=============

Bargate utilises two configuration files:

- bargate.conf - the main configuration file
- shares.conf - a list of file shares your users can access

bargate.conf
------------

On startup bargate looks in the following locations for a config file:

- /etc/bargate.conf
- /etc/bargate/bargate.conf
- /opt/bargate/bargate.conf

Once it finds a config file it stops searching, e.g. if /etc/bargate.conf exists
then the other config file locations are not checked.

Once you have installed bargate you will need to create a configuration file. 
Copy the sample config file to get started::

  cp /opt/bargate/etc/bargate.conf /etc/bargate.conf

The above command assumes you installed bargate into /opt/bargate

The minimum options you'll need to set are:

- :ref:`CONFIG_SECRET_KEY`
- :ref:`CONFIG_ENCRYPT_KEY`
- :ref:`CONFIG_DISABLE_APP`

bargate.conf is treated as a Python file - all configuration must adhere to 
Python syntax.

See :doc:`config_options` for a complete list of options to set.

shares.conf
-----------

Bargate should be configured with a list of file shares to present to the 
users, otherwise only 'Connect to server' (i.e. enter manually) functionality 
is available. These shares are configured in the shares config file, 
usually /etc/bargate/shares.conf (this path is configured via the 
:ref:`CONFIG_SHARES_CONFIG` parameter).

See :doc:`shares` to understand the syntax of this configuration file.

Once configured you'll need to override the dropdown-menus.html template as well.
