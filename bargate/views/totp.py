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

from flask import session, render_template, redirect, url_for, request, flash, abort, jsonify

from bargate import app
from bargate.lib import totp, user


@app.route('/totp/qrcode')
@app.login_required
def totp_qrcode_view():
	if not totp.user_enabled(session['username']):
		return totp.return_qrcode(session['username'])
	else:
		abort(403)


@app.route('/totp/enable', methods=['POST'])
@app.set_response_type('json')
@app.login_required
def totp_enable():
	if totp.user_enabled(session['username']):
		return jsonify({'code': 1, 'msg': 'Two step verification is already enabled on your account'})
	else:
		if 'token' not in request.form:
			return jsonify({'code': 1, 'msg': 'Please enter a verification code from the app on your mobile device'})

		if totp.verify_token(session['username'], request.form['token']):
			totp.enable_for_user(session['username'])
			return jsonify({'code': 0})
		else:
			return jsonify({'code': 1, 'msg': 'Invalid verification code'})


@app.route('/totp/disable', methods=['POST'])
@app.set_response_type('json')
@app.login_required
def totp_disable():
	if not totp.user_enabled(session['username']):
		return jsonify({'code': 0})
	else:
		if 'token' not in request.form:
			return jsonify({'code': 1, 'msg': 'Please enter a verification code from the app on your mobile device'})

		if totp.verify_token(session['username'], request.form['token']):
			totp.disable_for_user(session['username'])
			return jsonify({'code': 0})
		else:
			return jsonify({'code': 1, 'msg': 'Invalid verification code'})


@app.route('/verify', methods=['GET', 'POST'])
def totp_logon_view():
	if request.method == 'GET':
		if app.is_user_logged_in():
			return redirect(url_for(app.config['SHARES_DEFAULT']))
		elif 'username' in session:
			if totp.device_trusted(session['username']):
				return user.logon_ok()

		return render_template('login/totp.html', active="user")
	elif request.method == 'POST':
		# verify the token entered
		token = request.form['token']

		if totp.verify_token(session['username'], token):
			response = user.logon_ok()

			if request.form.get('trust', default="") == 'confirm':
				return totp.set_trust_cookie(response, session['username'])
			else:
				return response
		else:
			flash("Invalid two step code!", "alert-danger")
			return redirect(url_for('totp_logon_view'))
