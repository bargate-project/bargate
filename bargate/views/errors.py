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

from flask import g, jsonify, session, request

from bargate import app
from bargate.lib import errors


@app.errorhandler(400)
def error400(error):
	return errors.stderr("Bad request", "Your request was invalid or malformed, please try again.", 404)


@app.errorhandler(403)
def error403(error):
	return errors.stderr("Permission denied", "You do not have permission to perform that action.", 403)


@app.errorhandler(404)
def error404(error):
	return errors.stderr("Not found", "Sorry, I couldn't find what you requested.", 404)


@app.errorhandler(405)
def error405(error):
	return errors.stderr("Not allowed", "HTTP Method not allowed", 405)


@app.errorhandler(app.CsrfpException)
def csrfp_error(error):
	"""Handles CSRF protection exceptions"""

	if g.get('response_type', 'html') == 'json':
		return jsonify({'code': 400, 'msg': 'Your request failed to present a valid security token (CSRF protection)'})
	else:
		return errors.stderr("Security error",
			"Your browser failed to present a valid security token (CSRF protection token", 403)


@app.errorhandler(Exception)
def catchall_error_handler(error):
	app.logger.debug("fatal_error_handler()")
	"""Handles generic exceptions within the application, displaying the
	traceback if the application is running in debug mode."""

	# Get the traceback
	trace = str(traceback.format_exc())
	if app.debug:
		debug = trace
	else:
		debug = "Ask your system administrator to consult the error log for further information."

	if app.is_user_logged_in():
		username = session['username']
	else:
		username = 'Not logged in'

	message = type(error).__name__ + ": " + str(error)

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

{}
""".format(type(error).__name__, str(error), request.path, request.method, request.remote_addr,
			request.user_agent.string, request.user_agent.platform, request.user_agent.browser,
			request.user_agent.version, username, trace))

	return errors.fatalerr(u"fatal error ☹", message, debug)
