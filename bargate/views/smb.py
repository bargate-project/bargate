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

from flask import request, session, redirect, url_for, render_template, jsonify

from bargate import app


@app.login_required
@app.allow_disable
def endpoint_handler(path, action):
	return app.smblib.smb_action(request.endpoint, action, path)


@app.route('/smb/<action>/<epname>/', defaults={'path': ''})
@app.route('/smb/<action>/<epname>/<path:path>')
@app.set_response_type('json')
@app.login_required
@app.allow_disable
def smb_get_json(epname, action, path):
	return app.smblib.smb_action(epname, action, path)


@app.route('/smb', methods=['POST'])
@app.set_response_type('json')
@app.login_required
@app.allow_disable
def smb_post():
	if 'action' not in request.form:
		return jsonify({'code': 1, 'msg': 'No action specified'})

	if 'epname' not in request.form:
		return jsonify({'code': 1, 'msg': 'No endpoint name name specified'})

	if 'path' in request.form:
		app.logger.debug("path set to: " + request.form['path'])
		path = request.form['path']
	else:
		app.logger.debug("path not set in call to smb_post")
		path = ''

	return app.smblib.smb_action(request.form['epname'], request.form['action'], path)


@app.route('/other')
@app.login_required
@app.allow_disable
def other():
	return render_template('other.html', active='other', pwd='')


@app.route('/connect', methods=['GET', 'POST'])
@app.login_required
@app.allow_disable
def connect():
	if request.method == 'POST':
		server_uri = request.form['open_server_uri']
		session['custom_uri'] = server_uri
		session.modified = True
		return redirect(url_for('custom'))
	else:
		return render_template('custom.html', active='custom', pwd='')


@app.route('/custom/browse/', defaults={'action': 'browse', 'path': ''})
@app.route('/custom/browse', defaults={'action': 'browse', 'path': ''})
@app.route('/custom', defaults={'path': '', 'action': 'browse'})
@app.route('/custom/browse/<path:path>/', defaults={'action': 'browse'})
@app.route('/custom/browse/<path:path>', defaults={'action': 'browse'})
@app.route('/custom/<action>/<path:path>/')
@app.route('/custom/<action>/<path:path>')
@app.login_required
@app.allow_disable
def custom(path, action):
	if 'custom_uri' in session:
		if len(session['custom_uri']) == 0:
			return redirect(url_for('custom_server'))
	else:
		return redirect(url_for('custom_server'))

	return app.smblib.smb_action('custom', action, path)
