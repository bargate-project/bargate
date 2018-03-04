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

from flask import request, session, redirect, url_for, flash, abort, render_template, send_from_directory
from flask import current_app as app

from bargate.lib import aes, user, misc


@app.csrfp_exempt
@app.route('/', methods=['GET', 'POST'])
def login():
	if app.is_user_logged_in():
		return redirect(url_for(app.config['SHARES_DEFAULT']))
	else:
		if request.method == 'GET' or request.method == 'HEAD':
			next = request.args.get('next', default=None)
			return render_template('login/login.html', next=next)

		elif request.method == 'POST':

			result = user.auth(request.form['username'], request.form['password'])

			if not result:
				flash('Incorrect username and/or password', 'alert-danger')
				return redirect(url_for('login'))

			# Set the username in the session
			session['username']  = request.form['username'].lower()

			# Check if the user selected "remember me"
			session.permanent = False
			if app.config['REMEMBER_ME_ENABLED']:
				if request.form.get('rememberMe', default='') == 'confirm':
					session.permanent = True

			# Encrypt the password and store in the session
			session['id'] = aes.encrypt(request.form['password'], app.config['ENCRYPT_KEY'])

			# Check if two-factor is enabled for this account
			if app.config['TOTP_ENABLED']:
				from bargate.lib import totp

				if not totp.device_trusted(session['username']):
					if totp.user_enabled(session['username']):
						app.logger.debug('User "' + session['username'] +
							'" has two step enabled. Redirecting to two-step handler')
						return redirect(url_for('totp_logon_view'))

			# Successful logon without 2-step needed
			return user.logon_ok()


@app.route('/logout')
def logout():

	if app.is_user_logged_in():
		user.logout()
		flash('You have logged out successfully', 'alert-success')

	return redirect(url_for('login'))


@app.route('/nojs')
def nojs():
	return render_template('views/nojs.html')


@app.csrfp_exempt
@app.route('/portallogin', methods=['POST', 'GET'])
def portallogin():
	# cookie_name    = request.args.get('cookie0')
	cookie_content = request.args.get('cookie1').split(';')[0]

	decoded_cookie_content = misc.decode_session_cookie(cookie_content)
	json_cookie_content    = misc.flask_load_session_json(decoded_cookie_content)

	app.logger.debug('Decoded cookie username ' + json_cookie_content['username'])

	session['username']     = json_cookie_content['username']
	session['id']           = json_cookie_content['id']

	# verify this username and password we've been told to accept via cookie
	result = user.auth(session['username'], user.get_password())

	if not result:
		flash('Incorrect username and/or password', 'alert-danger')
		user.logout()
		return redirect(url_for('login'))
	else:
		session['logged_in']    = True
		return redirect(url_for(app.config['SHARES_DEFAULT']))


@app.route('/local/<path:filename>')
def local_static(filename):
	if app.config['LOCAL_STATIC_DIR']:
		return send_from_directory(app.config['LOCAL_STATIC_DIR'], filename)
	else:
		abort(404)


@app.route('/edit')
def edit_test():
	pass
