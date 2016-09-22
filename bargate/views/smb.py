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

import bargate
from bargate import app
from flask import Flask, request, session, redirect, url_for, render_template

################################################################################
#### SHARE HANDLER
		
@app.login_required
@app.allow_disable
def share_handler(path, action="browse"):

	## Get the path variable
	svrpath = app.sharesConfig.get(request.endpoint,'path')

	## Variable substition for username
	svrpath = svrpath.replace("%USERNAME%",session['username'])
	svrpath = svrpath.replace("%USER%",session['username'])

	## LDAP home dir substitution support
	if app.config['LDAP_HOMEDIR']:
		if 'ldap_homedir' in session:
			if not session['ldap_homedir'] == None:
				svrpath = svrpath.replace("%LDAP_HOMEDIR%",session['ldap_homedir'])

	## Get the display name
	display = app.sharesConfig.get(request.endpoint,'display')

	## What menu is active?
	menu = app.sharesConfig.get(request.endpoint,'menu')

	## Run the page!
	return bargate.lib.smb.connection(svrpath,request.endpoint,menu,display,action,path)

################################################################################

@app.route('/other')
@app.login_required
@app.allow_disable
def other():
	return render_template('other.html', active='shared',pwd='')

################################################################################

@app.route('/custom')
@app.login_required
@app.allow_disable
def custom_server():
	return render_template('custom.html', active='shared',pwd='')

################################################################################

@app.route('/c', methods=['GET','POST'], defaults={'path': '', 'action': 'browse'})
@app.route('/c/browse/<path:path>/', methods=['GET','POST'], defaults={'action': 'browse'})
@app.route('/c/<action>/<path:path>/', methods=['GET','POST'])
@app.login_required
@app.allow_disable
def custom(path,action="browse"):

	if request.method == 'POST':
		try:
			server_uri = request.form['open_server_uri']
			## validate the path...somehow?

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

	return bargate.lib.smb.connection(unicode(session['custom_uri']),"custom","shared",session['custom_uri'],action,path)
