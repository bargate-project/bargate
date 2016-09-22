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
if app.config['TOTP_ENABLED']:
	import bargate.lib.totp
import bargate.lib.user
import bargate.lib.userdata
from flask import Flask, request, session, redirect, url_for, flash, g, abort, make_response, render_template, send_from_directory
import mimetypes
import os 
import time
import json
import re
import werkzeug
from itsdangerous import base64_decode

################################################################################
# Default route (login or redirect to the default share if logged in)

@app.csrfp_exempt
@app.route('/', methods=['GET', 'POST'])
@app.allow_disable
def login():
	if app.is_user_logged_in():
		return redirect(url_for(app.config['SHARES_DEFAULT']))
	else:
		if request.method == 'GET' or request.method == 'HEAD':
			next = request.args.get('next',default=None)
			return render_template('login.html', next=next)

		elif request.method == 'POST':

			result = bargate.lib.user.auth(request.form['username'], request.form['password'])

			if not result:
				flash('Incorrect username and/or password','alert-danger')
				return redirect(url_for('login'))
			
			## Set the username in the session
			session['username']  = request.form['username'].lower()
			
			## Check if the user selected "Log me out when I close the browser"
			if app.config['REMEMBER_ME_ENABLED']:
				permanent = request.form.get('sec',default="")

				## Set session as permanent or not
				if permanent == 'sec':
					session.permanent = True
				else:
					session.permanent = False
			else:
				session.permanent = False

			## Encrypt the password and store in the session
			session['id'] = bargate.lib.aes.encrypt(request.form['password'],app.config['ENCRYPT_KEY'])

			## Check if two-factor is enabled for this account
			if app.config['TOTP_ENABLED']:
				if bargate.lib.totp.user_enabled(session['username']):
					app.logger.debug('User "' + session['username'] + '" has two step enabled. Redirecting to two-step handler')
					return redirect(url_for('totp_logon_view',next=request.form.get('next',default=None)))

			## Successful logon without 2-step needed
			return bargate.lib.user.logon_ok()


################################################################################
# LOGOUT

@app.route('/logout')
def logout():

	if app.is_user_logged_in():
		bargate.lib.userdata.save('logout',str(time.time()))
		bargate.lib.user.logout()
		flash('You have logged out successfully','alert-success')

	return redirect(url_for('login'))

################################################################################

@app.route('/about')
def about():
	return render_template('about.html', active='help')

################################################################################

@app.route('/about/changelog')
def changelog():
	return render_template('changelog.html', active='help')

################################################################################

@app.route('/nojs')
def nojs():
	return render_template('nojs.html')

################################################################################
# Portal login support (added for University of Sheffield)

@app.csrfp_exempt
@app.route('/portallogin', methods=['POST', 'GET'])
def portallogin():
	cookie_name    = request.args.get('cookie0')
	cookie_content = request.args.get('cookie1').split(';')[0]

	decoded_cookie_content = bargate.lib.core.decode_session_cookie(cookie_content)
	json_cookie_content    = bargate.lib.core.flask_load_session_json(decoded_cookie_content)

	app.logger.info('Decoded cookie username ' + json_cookie_content['username'])

	session['username']     = json_cookie_content['username']
	session['id']           = json_cookie_content['id']

	## verify this username and password we've been told to accept via cookie
	result = bargate.lib.user.auth(session['username'], bargate.lib.user.get_password())

	if not result:
		flash('Incorrect username and/or password','alert-danger')
		bargate.lib.user.logout()
		return redirect(url_for('login'))
	else:
		session['logged_in']    = True
		return redirect(url_for(app.config['SHARES_DEFAULT']))

################################################################################
# Support for an additional /local/ static files directory

@app.route('/local/<path:filename>')
def local_static(filename):
	if app.config['LOCAL_STATIC_DIR']:
	    return send_from_directory(app.config['LOCAL_STATIC_DIR'], filename)
	else:
		abort(404)
