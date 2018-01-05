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

from flask import request, render_template, session, make_response, g, jsonify

from bargate import app


def stderr(title, message, http_return_code=200):
	"""This function is called by other error functions to show the error to the
	end user. It takes a title, message and a further error type. If redirect
	is set then rather than show an error it will return the 'redirect' after
	setting the popup error flags so that after the redirect a popup error is
	shown to the user. Redirect should be a string returned from flask redirect().
	"""

	if g.get('response_type', 'html') == 'json':
		return jsonify({'code': 1, 'msg': title + ": " + message})
	else:
		debug = traceback.format_exc()
		return render_template('error.html', title=title, message=message, debug=debug), http_return_code


def exception_handler(ex, message=None):

	# Get the traceback
	trace = str(traceback.format_exc())
	if app.debug:
		debug = trace
	else:
		debug = "Ask your system administrator to consult the error log for further information."

	if 'username' in session:
		username = session['username']
	else:
		username = 'Not logged in'

	if message is None:
		message = str(ex)

	# Log the critical error (so that it goes to e-mail)
	app.logger.error("""Fatal Error
Exception Type:       {}
Exception Message:    {}
HTTP Path:            {}
HTTP Method:          {}
Client IP Address:    {}
User Agent:           {}
User Platform:        {}
User Browser:         {}
User Browser Version: {}
Username:             {}
Traceback:
{}
""".format(str(type(ex)), str(ex), request.path, request.method, request.remote_addr, request.user_agent.string,
			request.user_agent.platform, request.user_agent.browser, request.user_agent.version, username, trace))

	if g.get('response_type', 'html') == 'json':
		return jsonify({'code': 1, 'msg': "A fatal error occured: " + message})
	else:

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
		<h1>fatal error ☹</h1>
		<p>%s</p>
		<pre>%s</pre>
	</div>
	</body>
	</html>
	""" % (message, debug)

		return make_response(html, 500)
