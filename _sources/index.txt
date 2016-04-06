.. raw:: html

  <link rel="stylesheet" type="text/css" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.5.0/css/font-awesome.min.css">
  <link rel="stylesheet" type="text/css" href="https://fonts.googleapis.com/css?family=Oswald:700">
  <style type="text/css">
  .logo {
     margin-bottom:50px;
  } 
  .logo h1
  {
  	font-family: 'Oswald', sans-serif;
  	margin: 0px;
    padding: 0px;
  	font-size: 8em;
    text-align: center;
    line-height: 0.8;
  }
  </style>
  <div class="logo">
  <h1 class="logo"><i class="fa fa-university"></i></h1>
  <h1 class="logo">bargate</h1>
  </div>

bargate is an open source modern web interface for SMB/CIFS file servers.

Download
--------

- The latest stable version is: `1.4.0 <https://github.com/divad/bargate/releases/tag/v1.4.0/>`_
- The latest old-stable version is: `1.3.4 <https://github.com/divad/bargate/releases/tag/v1.3.4/>`_

GitHub
------

All development information and bug reporting can be found on `GitHub <https://github.com/divad/bargate>`_.

Overview
--------

bargate is a standalone web application which can be used to present existing SMB 
file servers to your users via a web browser. It is written in Python 
and runs on Linux. Bargate was written to provide users with a way of accessing 
existing CIFS/SMB file servers from the web in a secure way. Bargate is 
currently in use at the University of Southampton and the University of 
Sheffield. You can consider bargate stable and ready for production use.

bargate is a responsive HTML5 web application that thus works well on smartphones,
tablets or desktops. You can choose to integrate bargate with any SMB/CIFS file
server - bargate is known to work with Samba, Windows, Isilon, NetApp and 
Novell file servers.

bargate is highly configurable; your users may change how the application works
and how it looks. You may confifgure what file servers are available for the user
to access. bargate supports either LDAP, Kerberos or 'SMB' authentication.

Screenshots
-----------

.. image:: images/screenshot_14_desktop.png
.. image:: images/screenshot_14_mobile.png
.. image:: images/screenshot_14_settings.png

Contents
--------

.. toctree::
   :maxdepth: 3

   screenshots
   install
   deploy
   upgrade
   config
   config_options
   shares
   templates
   sso
