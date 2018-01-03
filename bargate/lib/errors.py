#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of Bargate.
#
# Bargate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bargate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bargate.  If not, see <http://www.gnu.org/licenses/>.

import traceback

from flask import render_template, make_response


def stderr(title, message):
	"""This function is called by other error functions to show the error to the
	end user. It takes a title, message and a further error type. If redirect
	is set then rather than show an error it will return the 'redirect' after
	setting the popup error flags so that after the redirect a popup error is
	shown to the user. Redirect should be a string returned from flask redirect().
	"""

	debug = traceback.format_exc()
	return render_template('error.html', title=title, message=message, debug=debug), 200


def fatalerr(title=u"fatal error ☹", message="Whilst processing your request an error occured", debug=""):
	# Build the response. Not using a template here to prevent any Jinja issues from causing this to fail.

	html = u"""
<!doctype html>
<html>
<head>
	<title>Fatal Error</title>
	<meta charset="utf-8" />
	<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<style type="text/css">
	body {
		background-color: #8B1820;
		color: #FFFFFF;
		margin: 0;
		padding: 0;
		font-family: "Open Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
	}
	h1 {
		font-size: 4em;
		font-weight: normal;
		margin: 0px;
	}
	div {
		width: 80%%;
		margin: 5em auto;
		padding: 50px;
		border-radius: 0.5em;
	}
	@media (max-width: 900px) {
		div {
			width: auto;
			margin: 0 auto;
			border-radius: 0;
			padding: 1em;
		}
	}
	</style>
</head>
<body>
<div>
	<h1>%s</h1>
	<p>%s</p>
	<pre>%s</pre>
</div>
</body>
</html>
""" % (title, message, debug)

	return make_response(html, 500)
