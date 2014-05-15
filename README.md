bargate
=======

Bargate is a web interface to CIFS/SMB servers. It is written in Python, uses libsmbclient for talking to file servers (specifically, pysmbc) and the user interface is based on Twitter Bootstrap. Bargate has been developed to provide the 'Filestore Web Access' application at the University of Southampton: https://fwa.soton.ac.uk. As such the code currently here is entirely written for Southampton and would require quite a lot of re-writing to work elsewhere.

The plan is to add features to Bargate in time to allow other people to use it without having to re-write a lot of code. If you're interested in using or extending Bargate please get in touch, especially if you're a UK academic institution. Development is happening at a rapid pace at the moment, so now is the time to contact us!

Screenshots
-----------

![screenshoot](http://davidrichardbell.files.wordpress.com/2014/04/screen-shot-2014-04-21-at-19-30-55.png)
![screenshoot](http://davidrichardbell.files.wordpress.com/2014/04/screen-shot-2014-04-21-at-19-36-28.png)

Roadmap
-----------

The roadmap is as follows:

* v1.0 - First stable release, entirely focused on Uni Southampton usage
* v1.1 - Introduce Isoptope based directory view, other feature packs, e.g
* v1.2 - Remove hard-coded Southampton university features
* v2.x - Switch to a partial-JSON output with rendering done on the client side
* v3.x - Introduce near-entirely JSON output mode, to allow for Android and iOS client apps to be written

This is only a rough plan.
