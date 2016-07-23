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

# pip install onetimepass
# pip install pyqrcode

from bargate import app
import os
import base64
import redis
from flask import g, Flask, session, render_template, redirect, url_for, request, flash, abort
import onetimepass
import pyqrcode
import StringIO

################################################################################

def generate_secret_key():
	return base64.b32encode(os.urandom(10)).decode('utf-8')

################################################################################

def get_secret_key(userid):
	return g.redis.get('totp.%s.key' % userid)

################################################################################

def get_uri(userid):
	## check the user has a key, if not generate it.
	otp_secret = get_secret_key(userid)

	if otp_secret == None:
		otp_secret = generate_secret_key()
		g.redis.set('totp.%s.key' % userid,otp_secret)

	return 'otpauth://totp/{0}?secret={1}&issuer={2}'.format(session['username'], otp_secret, app.config['TOTP_IDENT'])

################################################################################

def verify_token(userid, token):
	otp_secret = get_secret_key(userid)

	if otp_secret == None:
		return False
	else:
		return onetimepass.valid_totp(token, otp_secret)

################################################################################

def return_qrcode(userid):
	url = pyqrcode.create(get_uri(userid))
	stream = StringIO.StringIO()
	url.svg(stream, scale=5)
	return stream.getvalue().encode('utf-8'), 200, {
		'Content-Type': 'image/svg+xml',
		'Cache-Control': 'no-cache, no-store, must-revalidate',
		'Pragma': 'no-cache',
		'Expires': '0'}

################################################################################

def user_enabled(userid):
	totp_enable = g.redis.get('totp.%s.enabled' % userid)

	if totp_enable == None:
		return False
	else:
		return True
