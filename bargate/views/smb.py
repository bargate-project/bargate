#!/usr/bin/python
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

from flask import request, session, redirect, url_for, jsonify, abort

from bargate import app


@app.login_required
def endpoint_handler(path, action):
	app.logger.debug("endpoint_handler('" + path + "','" + action + "')")
	return app.smblib.smb_action(request.endpoint, action, path)


@app.route('/xhr', methods=['POST'])
@app.set_response_type('json')
@app.login_required
def smb_post():
	if 'action' not in request.form:
		return jsonify({'code': 1, 'msg': 'No action specified'})

	if request.form['action'] == 'connect':
		if not app.config['CONNECT_TO_ENABLED']:
			return jsonify({'code': 1, 'msg': 'The system administrator has disabled connecting to a custom server'})

		if 'path' not in request.form:
			return jsonify({'code': 1, 'msg': 'You must enter an address to connect to.'})

		path = request.form['path']
		session['custom_uri'] = path
		session.modified = True
		return jsonify({'code': 0})

	if 'epname' not in request.form:
		return jsonify({'code': 1, 'msg': 'No endpoint name name specified'})

	if 'path' in request.form:
		app.logger.debug("path set to: " + request.form['path'])
		path = request.form['path']
	else:
		app.logger.debug("path not set in call to smb_post")
		path = ''

	app.logger.debug("smb_post(): epname is: '" + request.form['epname'] + "', action is: '" +
		request.form['action'] + "', path is: '" + path + "'")

	return app.smblib.smb_action(request.form['epname'], request.form['action'], path)


@app.route('/xhr/<action>/<epname>/', defaults={'path': ''})
@app.route('/xhr/<action>/<epname>/<path:path>')
@app.set_response_type('json')
@app.login_required
def smb_get(epname, action, path):
	app.logger.debug("smb_get_json('" + epname + "','" + action + "','" + path + "')")
	return app.smblib.smb_action(epname, action, path)


@app.route('/custom/browse/', defaults={'action': 'browse', 'path': ''})
@app.route('/custom/browse', defaults={'action': 'browse', 'path': ''})
@app.route('/custom', defaults={'path': '', 'action': 'browse'})
@app.route('/custom/browse/<path:path>/', defaults={'action': 'browse'})
@app.route('/custom/browse/<path:path>', defaults={'action': 'browse'})
@app.route('/custom/<action>/<path:path>/')
@app.route('/custom/<action>/<path:path>')
@app.login_required
def smb_custom(path, action):
	if not app.config['CONNECT_TO_ENABLED']:
		abort(404)

	if 'custom_uri' in session:
		if len(session['custom_uri']) == 0:
			return redirect(url_for('custom_server'))
	else:
		return redirect(url_for('custom_server'))

	return app.smblib.smb_action('custom', action, path)
