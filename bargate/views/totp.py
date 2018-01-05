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

from flask import g, session, render_template, redirect, url_for, request, flash, abort

from bargate import app
from bargate.lib import totp, user


@app.route('/totp_qrcode_img')
@app.login_required
def totp_qrcode_view():
	if not totp.user_enabled(session['username']):
		return totp.return_qrcode(session['username'])
	else:
		abort(403)


@app.route('/2step', methods=['GET', 'POST'])
@app.login_required
def totp_user_view():
	if not totp.user_enabled(session['username']):
		if request.method == 'GET':
			return render_template('totp_enable.html', active="user")
		elif request.method == 'POST':
			token = request.form['totp_token']

			if totp.verify_token(session['username'], token):
				flash("Two step logon has been enabled for your account", "alert-success")
				g.redis.set('totp.%s.enabled' % session['username'], "True")
			else:
				flash("Invalid code! Two step logons could not be enabled", "alert-danger")

			return redirect(url_for('totp_user_view'))

	else:
		if request.method == 'GET':
			return render_template('totp_disable.html', active="user")
		elif request.method == 'POST':

			token = request.form['totp_token']

			if totp.verify_token(session['username'], token):
				g.redis.delete('totp.%s.enabled' % session['username'])
				g.redis.delete('totp.%s.key' % session['username'])
				flash("Two step logons have been disabled for your account", "alert-warning")
			else:
				flash("Invalid code! Two step logons were not disabled", "alert-danger")

			return redirect(url_for('totp_user_view'))


@app.route('/verify2step', methods=['GET', 'POST'])
def totp_logon_view():
	if request.method == 'GET':
		return render_template('totp_verify.html', active="user")
	elif request.method == 'POST':
		# verify the token entered
		token = request.form['totp_token']

		if totp.verify_token(session['username'], token):
			return user.logon_ok()
		else:
			flash("Invalid two step code!", "alert-danger")
			return redirect(url_for('totp_logon_view'))
