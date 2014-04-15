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
import random
import string
from werkzeug.urls import url_encode
from flask import Flask, g, request, redirect, session, url_for, abort, render_template, flash
from functools import wraps
from Crypto.Cipher import AES
# the following needs a later pycrypto than is in RHEL6.
#from Crypto import Random
import base64
import os
import datetime
import re

################################################################################

def render_page(template_name, **kwargs):

	## Send the standard urls required on all pages
	url_personal    = url_for('personal')
	url_mydocuments = url_for('personal',path='mydocuments')
	url_mydesktop   = url_for('personal',path='mydesktop')
	url_website     = url_for('webfiles')

	return render_template(template_name, url_personal=url_personal,
		url_mydocuments=url_mydocuments,
		url_mydesktop=url_mydesktop,
		url_website=url_website, **kwargs)

################################################################################

def session_logout():
	app.logger.info('User "' + session['username'] + '" logged out from "' + request.remote_addr + '" using ' + request.user_agent.string)
	session.pop('logged_in', None)
	session.pop('username', None)

################################################################################

def checkValidPathName(name):
	"""A very strict path checking function. It checks the string passed to it
	is a valid path - or not. If not it calls abort(400) - it throws a flask
	exception
	"""

	## VERY strict path allowed regex
	## a-z, A-Z, 0-9, _ . $ , [ ] ( )
	if not re.match('^[ a-zA-Z0-9_\.\%\,\$\(\)\[\]]{1,255}$',name):
		app.logger.error("checkValidPathName ABORT: " + name)
		abort(400)

################################################################################

def debugStrType(obj,name):
	if isinstance(obj, str):
		app.logger.info(name + " regular string")
	elif isinstance(obj, unicode):	
		app.logger.info(name + " unicode string")

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
			flash('<strong>Oops!</strong> You must login first.','alert-danger')
			## TODO take the next code from sysman - much improved over this.
			args = url_encode(request.args)
			return redirect(url_for('hero', next=request.script_root + request.path + "?" + args))
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
			flash('<strong>Service Temporarily Unavailable</strong><br/> Normal service will be restored as soon as possible.','alert-error')
			return render_template('hero.html', active='hero')
		return f(*args, **kwargs)
	return decorated_function

################################################################################

@app.before_request
def before_request():
	"""This function is run before the request is handled by Flask. At present it checks
	to make sure a valid CSRF token has been supplied if a POST request is made, sets
	the default theme, and tells out of date web browsers to foad.
	"""
	# Check for MSIE version <= 8.0, or links or lynx and if found, tell the
	# user to bugger off
	if (request.user_agent.browser == "msie" and int(round(float(request.user_agent.version))) <= 8):
		return render_template('foad.html')

	## Check CSRF key is valid
	if request.method == "POST":
		## login handler shouldn't have to be CSRF protected
		if request.endpoint == 'login':
			return

		## check csrf token is valid
		token = session.get('_csrf_token')
		if not token or token != request.form.get('_csrf_token'):
			if 'username' in session:
				app.logger.warning('CSRF protection alert: %s failed to present a valid POST token',session['username'])
			else:
				app.logger.warning('CSRF protection alert: a non-logged in user failed to present a valid POST token')

			### the user cannot have accidentally triggered this
			### so just throw a 403.
			abort(403)
			
	## Theme default
	if not 'theme' in session:
		session['theme'] = 'lumen'

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
	"""This is crude password generator. It is currently only used to generate
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

	# the following needs a later pycrypto version than is on RHEL6.
	#iv = Random.new().read(AES.block_size)
	iv = os.urandom(AES.block_size)
	
	c = AES.new(key,AES.MODE_CFB,iv)
	b64 = base64.b64encode(iv + c.encrypt(s))
	return b64

################################################################################

def aes_decrypt(s,key):
	"""This function is used to decrypt a base64-encoded
	AES CFB encrypted string. 
	Pass it the string to decrypt and the correct key.
	Returns an unencrypted string.
	"""

	binary = base64.b64decode(s)
	iv = binary[:16]
	e = binary[16:]
	c = AES.new(key,AES.MODE_CFB,iv)
	return c.decrypt(e)

def get_user_password():
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
	a list by name.
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
