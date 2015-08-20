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
import bargate.errors     
from werkzeug.urls import url_encode
from flask import Flask, request, redirect, session, url_for, abort, render_template, flash, g
from functools import wraps   ## used for login_required and downtime_check
from Crypto.Cipher import AES ## used for crypto of password
import base64                 ## used for crypto of password
import os                     ## used throughout
import datetime               ## used in ut_to_string, online functions
import re                     ## used in secure_filename
import redis                  ## used in before_request
from random import randint    ## used in before_request
import time                   ## used in before_request
import random                 ## used in pwgen            
import string                 ## used in pwgen
import ldap

# For cookie decode
from base64 import b64decode
from itsdangerous import base64_decode
import zlib
import json
import uuid

################################################################################

def render_page(template_name, **kwargs):
	"""A wrapper around Flask's render_template that adds commonly used variables to the page"""

	## Standard bookmarks needed on nearly all pages
	if not 'bookmarks' in kwargs:
		if 'username' in session:
			kwargs['bookmarks'] = bargate.settings.get_user_bookmarks()

	return render_template(template_name, **kwargs)

################################################################################

def session_logout():
	"""Ends the logged in user's login session. The session remains but it is marked as being not logged in."""

	app.logger.info('User "' + session['username'] + '" logged out from "' + request.remote_addr + '" using ' + request.user_agent.string)
	session.pop('logged_in', None)
	session.pop('username', None)
	session.pop('id', None)
	session.pop('ldap_homedir', None)

################################################################################

def ut_to_string(ut):
	"""Converts unix time to a formatted string for human consumption
	Used by smb.py for turning fstat results into human readable dates.
	"""
	return datetime.datetime.fromtimestamp(int(ut)).strftime('%Y-%m-%d %H:%M:%S %Z')

################################################################################

def login_required(f):
	"""This is a decorator function that when called ensures the user has logged in.
	Usage is as such: @bargate.core.login_required
	"""
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if session.get('logged_in',False) is False:
			flash('You must login first!','alert-danger')
			args = url_encode(request.args)
			return redirect(url_for('login', next=request.script_root + request.path + "?" + args))
		return f(*args, **kwargs)
	return decorated_function

################################################################################

def downtime_check(f):
	"""This is a decorator function that when called disables the view if the application
	is currently disabled. This allows selective disabling of parts of the application.
	Usage is as such: @bargate.core.downtime_check
	"""
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if app.config['DISABLE_APP']:
			flash('Service Temporarily Unavailable - Normal service will be restored as soon as possible.','alert-warning')
			bgnumber = randint(1,2)
			## don't use render_page as it loads bookmarks and that might not work
			return render_template('login.html', bgnumber=bgnumber)
		return f(*args, **kwargs)
	return decorated_function

################################################################################

@app.before_request
def before_request():
	"""This function is run before the request is handled by Flask. At present it checks
	to make sure a valid CSRF token has been supplied if a POST request is made, sets
	the default theme, tells out of date web browsers to foad, and connects to redis
	for user data storage.
	"""

	# Check for MSIE version <= 6.0
	if (request.user_agent.browser == "msie" and int(round(float(request.user_agent.version))) <= 6):
		return render_template('foad.html')

	## Connect to redis
	if app.config['REDIS_ENABLED']:
		try:
			g.redis = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=0)
			g.redis.get('foo')
		except Exception as ex:
			bargate.errors.fatal('Unable to connect to redis',str(ex))
			
	## Log user last access time
	if 'username' in session:
		bargate.settings.set_user_data('last',str(time.time()))
		bargate.core.record_user_activity(session['username'])

	## Check CSRF key is valid
	if request.method == "POST":
		## login handler and portal page shouldn't have to be CSRF protected
		if not request.endpoint in ('login', 'portallogin'):
			## check csrf token is valid
			token = session.get('_csrf_token')
			if not token or token != request.form.get('_csrf_token'):
				if 'username' in session:
					app.logger.warning('CSRF protection alert: %s failed to present a valid POST token',session['username'])
				else:
					app.logger.warning('CSRF protection alert: a non-logged in user failed to present a valid POST token')

				### the user should not have accidentally triggered this
				### so just throw a 400
				abort(400)

################################################################################

def generate_csrf_token():
	"""This function is used in __init__.py to generate a CSRF token for use
	in templates.
	"""

	if '_csrf_token' not in session:
		session['_csrf_token'] = pwgen(32)
	return session['_csrf_token']

################################################################################

def pwgen(length=16):
	"""This is very crude password generator. It is currently only used to generate
	a CSRF token.
	"""

	urandom = random.SystemRandom()
	alphabet = string.ascii_letters + string.digits
	return str().join(urandom.choice(alphabet) for _ in range(length))

################################################################################

def aes_encrypt(s,key):
	"""This function is used to encrypt a string via AES.
	Pass it the string to encrypt and the key to use to do so.
	Returns a base64 encoded string using AES CFB.
	"""
	
	## https://www.dlitz.net/software/pycrypto/api/current/Crypto.Cipher.blockalgo-module.html#MODE_CFB
	## CFB does not require padding
	## 32-bit key is required (AES256)
	
	if len(key) != 32:
		bargate.errors.fatal('Configuration Error','The Bargate configuration is invalid. The ENCRYPT_KEY must be exactly 32-bytes long.')

	# Create the IV (Initialization Vector)
	iv = os.urandom(AES.block_size)
	
	## Create the cipher with the key, mode and iv
	c = AES.new(key,AES.MODE_CFB,iv)
	
	## Base 64 encode the iv and the encrypted data together
	b64 = base64.b64encode(iv + c.encrypt(s))
	
	## return the base64 encoded string
	return b64

################################################################################

def aes_decrypt(s,key):
	"""This function is used to decrypt a base64-encoded
	AES CFB encrypted string. 
	Pass it the string to decrypt and the correct key.
	Returns an unencrypted string.
	"""

	# Get the block size for AES
	block_size = AES.block_size
	
	# Base64 decode the encrypted data
	binary = base64.b64decode(s)

	# Pull out the IV (Initialization Vector) which is the first N bytes where N is the block size 
	iv = binary[:block_size]
	
	# Pull out the data
	e = binary[block_size:]
	
	# Set up the cipher object with the key, the mode (CFB) and the IV
	c = AES.new(key,AES.MODE_CFB,iv)
	
	# return decrypted data
	return c.decrypt(e)
	
################################################################################


def get_user_password():
	"""This function returns the user's decrypted password
	so as to use to authenticate somewhere else, e.g. to Kerberos
	to ensure that a permission denied error isn't caused by the user's password changing.
	"""
	return bargate.core.aes_decrypt(session['id'],app.config['ENCRYPT_KEY'])

################################################################################

def get_smbc_auth(server,share,workgroup,username,password):
	"""Returns authentication information for SMB/CIFS as required
	by the pysmbc module
	"""
	return (app.config['SMB_WORKGROUP'],session['username'],bargate.core.get_user_password())

################################################################################

def sort_by_name(left,right):
	"""A cmp function for the python sorted() function. Use to sort
	a list by name. Used by smb.py directory entry sorting.
	"""
	return cmp(left['name'].lower(),right['name'].lower())

################################################################################

def str_size(size):
	"""Takes an integer representing number of bytes and returns it
	as a human readable size, either bytes, kilobytes, megabytes or gigabytes.
	"""
	# Default to bytes as the type
	t="bytes"
	
	## Make sure it is an int
	size = int(size)

	if size > 1024:

		if size > 1024*1024*1024:
			size = float(size) / (1024.0*1024.0*1024.0)
			t="GB"

		elif size > 1048576:
			size = float(size) / (1024.0*1024.0)
			t="MB"
		else:
			size = float(size) / 1024.0
			t="KB"

		size = round(size,1)

	return str(size) + " " + t
	
################################################################################

def banned_file(filename):
	"""Takes a filename string and checks to see if has a banned
	file extension. Returns True or False.
	"""

	if '.' not in filename:
		return False

	elif filename.rsplit('.', 1)[1] in app.config['BANNED_EXTENSIONS']:
		return True

	else:
		return False

################################################################################

def secure_filename(filename):
	r"""Pass it a filename and it will return a secure version of it.  This
    filename can then safely be stored on a regular file system and passed
    to :func:`os.path.join`.  The filename returned is an ASCII only string
    for maximum portability.

    On windows system the function also makes sure that the file is not
    named after one of the special device files.

    >>> secure_filename("My cool movie.mov")
    'My_cool_movie.mov'
    >>> secure_filename("../../../etc/passwd")
    'etc_passwd'
    >>> secure_filename(u'i contain cool \xfcml\xe4uts.txt')
    'i_contain_cool_umlauts.txt'

    The function might return an empty filename.  It's your responsibility
    to ensure that the filename is unique and that you generate random
    filename if the function returned an empty one.

	This is a modified version of the werkzeug secure filename modified
	for bargate to allow spaces in filenames.

    .. versionadded:: 0.5

    :param filename: the filename to secure
    """

	if isinstance(filename, unicode):
		from unicodedata import normalize
		filename = normalize('NFKD', filename).encode('ascii', 'ignore')

	for sep in os.path.sep, os.path.altsep:
		if sep:
			filename = filename.replace(sep, ' ')

	regex = re.compile(r'[^ A-Za-z0-9_.-]')
	#filename = str(regex.sub('', '_'.join(filename.split() ) ))     .strip('._')
	filename = str(regex.sub('_',filename))

    # on nt a couple of special files are present in each folder.  We
    # have to ensure that the target file is not such a filename.  In
    # this case we prepend an underline
	windows_device_files = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1', 'LPT2', 'LPT3', 'PRN', 'NUL')

	if os.name == 'nt' and filename and filename.split('.')[0].upper() in windows_device_files:
		filename = '_' + filename

	return filename

################################################################################

def poperr_set(title,message):
	"""This function will create and show a
	popup dialog error on the next time a page
	is loaded. Use this before running a redirect.
	"""

	session['popup_error'] = True
	session['popup_error_title'] = title
	session['popup_error_message'] = message

################################################################################

def poperr_get():
	"""This function clears any currently set error popup. It is only to be
	called from inside a jinja template
	"""

	title = session['popup_error_title']
	message = session['popup_error_message']

	## clear the session
	session['popup_error'] = False
	session['popup_error_title'] = ""
	session['popup_error_message'] = ""
	
	return (title,message)

################################################################################
#### Authentication

def auth_user(username, password):
	app.logger.debug("bargate.core.auth_user " + username)

	if len(username) == 0:
		app.logger.debug("bargate.core.auth_user empty username")
		return False
	if len(password) == 0:
		app.logger.debug("bargate.core.auth_user empty password")
		return False

	if app.config['AUTH_TYPE'] == 'kerberos':
		app.logger.debug("bargate.core.auth_user auth type kerberos")

		## Kerberos authentication.
		## As of May 2015, DO NOT USE THIS. checkPassword does not verify the KDC is the right one.
		## Of course, this can only be verified if the local machine is actually joined to the domain? and thus has a local host/ principal?
		try:
			kerberos.checkPassword(request.form['username'], request.form['password'], app.config['KRB5_SERVICE'], app.config['KRB5_DOMAIN'])
		except kerberos.BasicAuthError as e:
			return False
		except kerberos.KrbError as e:
			flash('Unexpected kerberos authentication error: ' + e.__str__(),'alert-danger')
			return False
		except kerberos.GSSError as e:
			flash('Unexpected kerberos gss authentication error: ' + e.__str__(),'alert-danger')
			return False

		return True

	elif app.config['AUTH_TYPE'] == 'ldap':
		app.logger.debug("bargate.core.auth_user auth type ldap")

		## LDAP auth. This is preferred as of May 2015 due to issues with python-kerberos.

		## connect to LDAP and turn off referals
		l = ldap.initialize(app.config['LDAP_URI'])
		l.set_option(ldap.OPT_REFERRALS, 0)

		## and bind to the server with a username/password if needed in order to search for the full DN for the user who is logging in.
		try:
			if app.config['LDAP_ANON_BIND']:
				l.simple_bind_s()
			else:
				l.simple_bind_s( (app.config['LDAP_BIND_USER']), (app.config['LDAP_BIND_PW']) )
		except ldap.LDAPError as e:
			flash('Internal Error - Could not connect to LDAP directory: ' + str(e),'alert-danger')
			app.logger.error("Could not bind to LDAP: " + str(e))
			abort(500)


		app.logger.debug("bargate.core.auth_user ldap searching for username in base " + app.config['LDAP_SEARCH_BASE'] + " looking for attribute " + app.config['LDAP_USER_ATTRIBUTE'])

		## Now search for the user object to bind as
		try:
			results = l.search_s(app.config['LDAP_SEARCH_BASE'], ldap.SCOPE_SUBTREE,(app.config['LDAP_USER_ATTRIBUTE']) + "=" + username)
		except ldap.LDAPError as e:
			app.logger.debug("bargate.core.auth_user no object found in ldap")
			return False

		app.logger.debug("bargate.core.auth_user ldap found results from dn search")
	
		## handle the search results
		for result in results:
			dn	= result[0]
			attrs	= result[1]

			if dn == None:
				## No dn returned. Return false.
				return False

			else:
				app.logger.debug("bargate.core.auth_user ldap found dn " + str(dn))

				## Found the DN. Yay! Now bind with that DN and the password the user supplied
				try:
					app.logger.debug("bargate.core.auth_user ldap attempting ldap simple bind as " + str(dn))
					lauth = ldap.initialize(app.config['LDAP_URI'])
					lauth.set_option(ldap.OPT_REFERRALS, 0)
					lauth.simple_bind_s( (dn), (password) )
				except ldap.LDAPError as e:
					## password was wrong
					app.logger.debug("bargate.core.auth_user ldap bind failed as " + str(dn))
					return False

				app.logger.debug("bargate.core.auth_user ldap bind succeeded as " + str(dn))

				## Should we use the ldap home dir attribute?
				if app.config['LDAP_HOMEDIR']:
					## Now look up the LDAP HOME ATTRIBUTE as well
					if (app.config['LDAP_HOME_ATTRIBUTE']) in attrs:
						if type(attrs[app.config['LDAP_HOME_ATTRIBUTE']]) is list:
							homedir_attribute = attrs[app.config['LDAP_HOME_ATTRIBUTE']][0]
						else:
							homedir_attribute = str(attrs[app.config['LDAP_HOME_ATTRIBUTE']	])

						if homedir_attribute == None:
							app.logger.error('ldap_get_homedir returned None for user ' + username)
							flash("Profile Error: I could not find your home directory location","alert-danger")
							abort(500)
						else:
							session['ldap_homedir'] = homedir_attribute
							app.logger.debug('User "' + username + '" LDAP home attribute ' + session['ldap_homedir'])

							if app.config['LDAP_HOMEDIR_IS_UNC']:
								if session['ldap_homedir'].startswith('\\\\'):
									session['ldap_homedir'] = session['ldap_homedir'].replace('\\\\','smb://',1)
								session['ldap_homedir'] = session['ldap_homedir'].replace('\\','/')
					
							## Overkill but log it again anyway just to make sure we really have the value we think we should
							app.logger.debug('User "' + username + '" home SMB path ' + session['ldap_homedir'])		

				## Return that LDAP auth succeeded
				return True

		## Catch all return false for LDAP auth
		return False

	else:
		flash('Internal Error - Unknown or incorrect authentication type configured','alert-danger')
		app.logger.error("Critical Error - Unknown or incorrect authentication type configured")
		abort(500)


################################################################################

def record_user_activity(user_id,expire_minutes=1440):
    now = int(time.time())
    expires = now + (expire_minutes * 60) + 10

    all_users_key = 'online-users/%d' % (now // 60)
    user_key = 'user-activity/%s' % user_id
    p = g.redis.pipeline()
    p.sadd(all_users_key, user_id)
    p.set(user_key, now)
    p.expireat(all_users_key, expires)
    p.expireat(user_key, expires)
    p.execute()

def get_user_last_activity(user_id):
    last_active = g.redis.get('user-activity/%s' % user_id)
    if last_active is None:
        return None
    return datetime.utcfromtimestamp(int(last_active))

def list_online_users(minutes=15):
    if minutes > 86400:
        minutes = 86400
    current = int(time.time()) // 60
    minutes = xrange(minutes)
    return g.redis.sunion(['online-users/%d' % (current - x)
                         for x in minutes])

################################################################################
#### Cookie decode for portal login

def decode_session_cookie(cookie_data):
	compressed = False
	payload    = cookie_data

	if payload.startswith(b'.'):
		compressed = True
		payload = payload[1:]

	data = payload.split(".")[0]
	data = base64_decode(data)
	if compressed:
		data = zlib.decompress(data)

	return data

def flask_load_session_json(value):

	def object_hook(obj):
		if (len(obj) != 1):
			return obj
		the_key, the_value = next(obj.iteritems())
		if the_key == 't':
			return str(tuple(the_value))
		elif the_key == 'u':
			return str(uuid.UUID(the_value))
		elif the_key == 'b':
			return str(b64decode(the_value))
		elif the_key == 'm':
			return str(Markup(the_value))
		elif the_key == 'd':
			return str(parse_date(the_value))
		return obj

	return json.loads(value, object_hook=object_hook)

