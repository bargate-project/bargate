Bargate
=======

Bargate is a web interface to CIFS/SMB servers. It is written in Python, uses libsmbclient for talking to file servers (specifically, pysmbc) and the user interface is based on Twitter Bootstrap. Bargate has been developed to provide the 'Filestore Web Access' application at the University of Southampton: https://fwa.soton.ac.uk, however it has been written to allow third parties (especially other Universities) to utilise the application themselves.

If you're interested in using or extending Bargate please get in touch, especially if you're a UK academic institution. Development is happening at a rapid pace at the moment, so now is the time to contact us!

Because Bargate is written using Bootstrap 3 it is 'mobile first' and features a responsive design, making Bargate work equally well on phones, tablets or desktops. Bargate works with any SMB server that libsmbclient supports (essentially anything standards compliant).

Screenshots
-----------

![screenshoot](http://davidrichardbell.files.wordpress.com/2014/04/screen-shot-2014-04-21-at-19-30-55.png)
![screenshoot](http://davidrichardbell.files.wordpress.com/2014/04/screen-shot-2014-04-21-at-19-36-28.png)

Roadmap
-----------

The roadmap is as follows:

* v1.0 - First stable release
* v1.1 - Introduce Isoptope based directory view
* v1.2 - Fully remove all UoS custom templates from github release
* v1.3 - Add native PDF support via pdf.js
* v2.x - Switch to a partial-JSON output with rendering done on the client side
* v3.x - Introduce near-entirely JSON output mode, to allow for Android and iOS client apps to be written

This plan will be updated on a regular basis.
