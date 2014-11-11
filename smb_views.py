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

from bargate import app
import bargate.core
from flask import Flask, request, session, redirect, url_for

@app.route('/other')
@bargate.core.login_required
@bargate.core.downtime_check
def other():
	return bargate.core.render_page('other.html', active='shared',pwd='')

@app.route('/custom')
@bargate.core.login_required
@bargate.core.downtime_check
def custom_server():
	return bargate.core.render_page('custom.html', active='shared',pwd='')

@app.route('/c', methods=['GET','POST'], defaults={'path': ''})
@app.route('/c/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def custom(path):

	if request.method == 'POST':
		try:
			server_uri = request.form['open_server_uri']
			## TODO validate the path...somehow?

			session['custom_uri'] = server_uri
			session.modified = True
			## redirect to custom so its now a GET request
			return redirect(url_for('custom'))

		except KeyError as ex:
			## standard POST, not setting up a new server
			pass

	## ensure the custom_uri is set
	if 'custom_uri' in session:
		if len(session['custom_uri']) == 0:
			return redirect(url_for('custom_server'))
	else:
		return redirect(url_for('custom_server'))

	return bargate.smb.connection(unicode(session['custom_uri']),"custom","shared",session['custom_uri'],path)
