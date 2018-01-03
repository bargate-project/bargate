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
def share_handler(path, action):
	if action == 'browse':
		app.smblib.set_response('html')
	else:
		app.smblib.set_response('http')

	return app.smblib.smb_action(request.endpoint, action, path)


@app.route('/smb/<action>/<share>/', defaults={'path': ''})
@app.route('/smb/<action>/<share>/<path:path>')
@app.login_required
@app.allow_disable
def smb_get_json(share, action, path):
	app.smblib.set_response('json')
	return app.smblib.smb_action(share, action, path)


@app.route('/smb', methods=['POST'])
@app.login_required
@app.allow_disable
def smb_post():
	app.smblib.set_response('json')

	if 'action' not in request.form:
		return jsonify({'code': 1, 'msg': 'No action specified'})

	if 'share' not in request.form:
		return jsonify({'code': 1, 'msg': 'No share name specified'})

	if 'path' in request.form:
		app.logger.debug("path set to: " + request.form['path'])
		path = request.form['path']
	else:
		app.logger.debug("path not set in call to smb_post")
		path = ''

	return app.smblib.smb_action(request.form['share'], request.form['action'], path)


@app.route('/other')
@app.login_required
@app.allow_disable
def other():
	return render_template('other.html', active='shared', pwd='')


@app.route('/custom')
@app.login_required
@app.allow_disable
def custom_server():
	return render_template('custom.html', active='shared', pwd='')


@app.route('/c', methods=['GET', 'POST'], defaults={'path': '', 'action': 'browse'})
@app.route('/c/browse/<path:path>', methods=['GET', 'POST'], defaults={'action': 'browse'})
@app.route('/c/browse/<path:path>/', methods=['GET', 'POST'], defaults={'action': 'browse'})
@app.route('/c/<action>', methods=['GET', 'POST'], defaults={'path': ''})
@app.route('/c/<action>/', methods=['GET', 'POST'], defaults={'path': ''})
@app.route('/c/<action>/<path:path>', methods=['GET', 'POST'])
@app.route('/c/<action>/<path:path>/', methods=['GET', 'POST'])
@app.login_required
@app.allow_disable
def custom(path, action="browse"):

	if request.method == 'POST':
		try:
			server_uri = request.form['open_server_uri']
			# validate the path...somehow?

			session['custom_uri'] = server_uri
			session.modified = True
			# redirect to custom so its now a GET request
			return redirect(url_for('custom'))

		except KeyError:
			# standard POST, not setting up a new server
			pass

	# ensure the custom_uri is set
	if 'custom_uri' in session:
		if len(session['custom_uri']) == 0:
			return redirect(url_for('custom_server'))
	else:
		return redirect(url_for('custom_server'))

	return app.smblib.smb_action(unicode(session['custom_uri']),
		"custom", "shared", session['custom_uri'], action, path)
