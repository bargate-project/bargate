Templates
=========

As a Flask based web application, bargate uses the Jinja2 template system to 
generate the HTML output that your users see. In order to let you customise this
output Bargate can be configured to specify an alternative 'local templates' 
directory. If files are placed in this directory then they will be used in
preference to those built into bargate.

In this way you can selectivley override parts of Bargate's output and customise
what the interface looks like, what menu items exist, etc. Any bargate template
can be overridden but it is recommended that you only override templates designed
for you to do so.

Set up local templates
----------------------

To get started you need to set the :ref:`CONFIG\_LOCAL\_TEMPLATE\_DIR` option in 
bargate.conf to point at a directory where you will place your local templates.
You then need to restart bargate so it will notice the new config option, on startup
it should output something like this to the log file::

  2016-03-28 19:25:47,119 INFO: site-specific templates will be loaded from: /opt/bargate/local_templates/

You will now need to create files in the directory matching names that Bargate looks
for. Please see the section below for the names of the files you can override 
and what each file is for.

All template names end in '.html', for brevity this is omitted below.

Templates you should edit
-------------------------


=================   ============================================================
Name                Function
=================   ============================================================
dropdown-menus      drop-down menus intended for links to file servers/shares
help-menu           menu intended for items relating to user help/about
login-body          the top of the <body> element of the login page
login-container     the login page header area (top of the login box)
login-footer        the login page footer area (bottom of the login box)
login-head          the <head> part of the login page
other               a menu of smb file servers to connect to
user-menu           part of the 'bargate menu' - between settings and logout
=================   ============================================================

Templates you can edit
-------------------------

=================   ============================================================
Name                Function
=================   ============================================================
custom              connect to server form
error               the generic error page
header-links        CSS file imports
javascript          javascript file imports
login               login page/form
nojs                page shown when the user has javascript disabled
totp_verify         page shown when the user must enter their two factor token
=================   ============================================================

Templates you should not edit
-----------------------------

=================   ============================================================
Name                Function
=================   ============================================================
about               bargate about page
bookmarks           bookmark manager page
bookmarks-menu      drop down menu listing user bookmarks
breadcrumbs         breadcrumb generation code
changelog           bargate changelog
directory-grid      the grid-layout directory view
directory-list      the list-layout directory view
directory-menus     right click menus for directory view
directory-modals    pop-up modals for directory view
foad                page shown to users with an out-of-date web browser
layout              master template for all pages
online              list of all online users
settings            user settings page
totp_disable        two-factor authentication disable form
totp_enable         two-factor authentication enable form
search              search results view
=================   ============================================================

