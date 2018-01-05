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

from flask import g, jsonify

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

	return errors.exception_handler(error)
