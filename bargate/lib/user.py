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

import time

from flask import request, redirect, session, url_for, abort, flash

from bargate import app
from bargate.lib import aes, userdata

# load kerberos or ldap auth if needed
if app.config['AUTH_TYPE'] == 'kerberos' or app.config['AUTH_TYPE'] == 'krb5':
	try:
		import kerberos
	except ImportError as ex:
		app.error = "AUTH_TYPE is set to kerberos but the required module 'kerberos' is not installed."

elif app.config['AUTH_TYPE'] == 'ldap':
	try:
		import ldap
	except ImportError as ex:
		app.error = "AUTH_TYPE is set to ldap but the required module 'ldap' is not installed."


def get_password():
	"""This function returns the user's decrypted password"""
	return aes.decrypt(session['id'], app.config['ENCRYPT_KEY'])


def logon_ok():
	"""This function is called post-logon or post TOTP logon to complete the logon sequence"""

	# Mark as logged on
	session['logged_in'] = True

	# Log a successful login
	app.logger.info('User "' + session['username'] + '" logged in from "' + request.remote_addr +
		'" using ' + request.user_agent.string)

	# Record the last login time
	if app.config['USER_STATS_ENABLED']:
		userdata.save('login', time.time())

	# determine if "next" variable is set (the URL to be sent to)
	next = request.form.get('next', default=None)
	if 'next' in session:
		next = session['next']
		session.pop('next', None)

	if next is None:
		return redirect(url_for(app.config['SHARES_DEFAULT']))
	else:
		return redirect(next)


def auth(username, password):
	app.logger.debug("bargate.lib.user.auth " + username)

	if len(username) == 0:
		app.logger.debug("bargate.lib.user.auth empty username")
		return False

	if len(password) == 0:
		app.logger.debug("bargate.lib.user.auth empty password")
		return False

	if app.config['AUTH_TYPE'] == 'kerberos' or app.config['AUTH_TYPE'] == 'krb5':
		app.logger.debug("bargate.lib.user.auth auth type kerberos")

		# Kerberos authentication.
		try:
			kerberos.checkPassword(request.form['username'], request.form['password'],
				app.config['KRB5_SERVICE'], app.config['KRB5_DOMAIN'])
		except kerberos.BasicAuthError as e:
			return False
		except kerberos.KrbError as e:
			flash('Unexpected kerberos authentication error: ' + e.__str__(), 'alert-danger')
			return False
		except kerberos.GSSError as e:
			flash('Unexpected kerberos gss authentication error: ' + e.__str__(), 'alert-danger')
			return False

		app.logger.debug("bargate.lib.user.auth auth kerberos success")
		return True

	elif app.config['AUTH_TYPE'] == 'smb':
		app.logger.debug("bargate.lib.user.auth auth type smb")
		return app.smblib.smb_auth(request.form['username'], request.form['password'])

	elif app.config['AUTH_TYPE'] == 'ldap':
		app.logger.debug("bargate.lib.user.auth auth type ldap")

		# LDAP auth. This is preferred as of May 2015 due to issues with python-kerberos.

		# connect to LDAP and turn off referals
		ldap_conn = ldap.initialize(app.config['LDAP_URI'])
		ldap_conn.set_option(ldap.OPT_REFERRALS, 0)

		# and bind to the server with a username/password if needed in
		# order to search for the full DN for the user who is logging in
		try:
			if app.config['LDAP_ANON_BIND']:
				ldap_conn.simple_bind_s()
			else:
				ldap_conn.simple_bind_s((app.config['LDAP_BIND_USER']), (app.config['LDAP_BIND_PW']))
		except ldap.LDAPError as e:
			flash('Internal Error - Could not connect to LDAP server: ' + str(e), 'alert-danger')
			app.logger.error("Could not bind to LDAP: " + str(e))
			return False

		app.logger.debug("bargate.lib.user.auth ldap searching for username in base " +
			app.config['LDAP_SEARCH_BASE'] + " looking for attribute " + app.config['LDAP_USER_ATTRIBUTE'])

		# Now search for the user object to bind as
		try:
			results = ldap_conn.search_s(app.config['LDAP_SEARCH_BASE'], ldap.SCOPE_SUBTREE,
				app.config['LDAP_USER_ATTRIBUTE'] + "=" + username)
		except ldap.LDAPError as e:
			app.logger.debug("bargate.lib.user.auth no object found in ldap")
			return False

		app.logger.debug("bargate.lib.user.auth ldap found results from dn search")

		# handle the search results
		for result in results:
			dn = result[0]
			attrs = result[1]

			if dn is None:
				# No dn returned. Return false.
				return False

			else:
				app.logger.debug("bargate.lib.user.auth ldap found dn " + str(dn))

				# Found the DN. Yay! Now bind with that DN and the password the user supplied
				try:
					app.logger.debug("bargate.lib.user.auth ldap attempting ldap simple bind as " + str(dn))
					lauth = ldap.initialize(app.config['LDAP_URI'])
					lauth.set_option(ldap.OPT_REFERRALS, 0)
					lauth.simple_bind_s((dn), (password))
				except ldap.LDAPError as e:
					# password was wrong
					app.logger.debug("bargate.lib.user.auth ldap bind failed as " + str(dn))
					return False

				app.logger.debug("bargate.lib.user.auth ldap bind succeeded as " + str(dn))

				# Should we use the ldap home dir attribute?
				if app.config['LDAP_HOMEDIR']:
					# Now look up the LDAP HOME ATTRIBUTE as well
					if (app.config['LDAP_HOME_ATTRIBUTE']) in attrs:
						if type(attrs[app.config['LDAP_HOME_ATTRIBUTE']]) is list:
							homedir_attribute = attrs[app.config['LDAP_HOME_ATTRIBUTE']][0]
						else:
							homedir_attribute = str(attrs[app.config['LDAP_HOME_ATTRIBUTE']])

						if homedir_attribute is None:
							app.logger.error('ldap_get_homedir returned None for user ' + username)
							flash("Profile Error: I could not find your home directory location", "alert-danger")
							abort(500)
						else:
							session['ldap_homedir'] = homedir_attribute
							app.logger.debug('User "' + username + '" LDAP home attribute ' + session['ldap_homedir'])

							if app.config['LDAP_HOMEDIR_IS_UNC']:
								if session['ldap_homedir'].startswith('\\\\'):
									session['ldap_homedir'] = session['ldap_homedir'].replace('\\\\', 'smb://', 1)
								session['ldap_homedir'] = session['ldap_homedir'].replace('\\', '/')

							# Overkill but log it again anyway just to make
							# sure we really have the value we think we should
							app.logger.debug('User "' + username + '" home SMB path ' + session['ldap_homedir'])

				# Return that LDAP auth succeeded
				app.logger.debug("bargate.lib.user.auth ldap success")
				return True

		# Catch all return false for LDAP auth
		return False


def logout():
	"""Ends the logged in user's login session. The session remains but it is marked as being not logged in."""

	app.logger.info('User "' + session['username'] + '" logged out from "' +
		request.remote_addr + '" using ' + request.user_agent.string)
	session.pop('logged_in', None)
	session.pop('username', None)
	session.pop('id', None)
	session.pop('ldap_homedir', None)
