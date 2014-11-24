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
import datetime               ## used in ut_to_string
import re                     ## used in secure_filename
import redis                  ## used in before_request
from random import randint    ## used in before_request
import time                   ## used in before_request
import random                 ## used in pwgen            
import string                 ## used in pwgen

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
			## TODO take the next code from sysman - much improved over this.
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
			bgnumber = randint(1,17)
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

	## Check CSRF key is valid
	if request.method == "POST":
		## login handler shouldn't have to be CSRF protected
		if not request.endpoint == 'login':
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
