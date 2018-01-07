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

import os
import base64
import StringIO
import hashlib
from datetime import datetime, timedelta

from flask import g, session, request
from itsdangerous import TimestampSigner, BadData

from bargate import app

try:
	import onetimepass
except ImportError as ex:
	app.error = "TOTP is enabled but the required module 'onetimepass' is not installed."

try:
	import pyqrcode
except ImportError as ex:
	app.error = "TOTP is enabled but the required module 'pyqrcode' is not installed."


def generate_secret_key():
	return base64.b32encode(os.urandom(10)).decode('utf-8')


def get_secret_key(userid):
	return g.redis.get('totp.%s.key' % userid)


def get_uri(userid):
	# check the user has a key, if not generate it.
	otp_secret = get_secret_key(userid)

	if otp_secret is None:
		otp_secret = generate_secret_key()
		g.redis.set('totp.%s.key' % userid, otp_secret)

	return 'otpauth://totp/{0}?secret={1}&issuer={2}'.format(session['username'], otp_secret, app.config['TOTP_IDENT'])


def verify_token(userid, token):
	otp_secret = get_secret_key(userid)

	if otp_secret is None:
		return False
	else:
		return onetimepass.valid_totp(token, otp_secret)


def return_qrcode(userid):
	url = pyqrcode.create(get_uri(userid))
	stream = StringIO.StringIO()
	url.svg(stream, scale=5)
	return stream.getvalue().encode('utf-8'), 200, {
		'Content-Type': 'image/svg+xml',
		'Cache-Control': 'no-cache, no-store, must-revalidate',
		'Pragma': 'no-cache',
		'Expires': '0'}


def user_enabled(userid):
	totp_enable = g.redis.get('totp.%s.enabled' % userid)

	if totp_enable is None:
		return False
	else:
		return True


def enable_for_user(userid):
	g.redis.set('totp.%s.enabled' % userid, "True")


def disable_for_user(userid):
	g.redis.delete('totp.%s.enabled' % userid)
	g.redis.delete('totp.%s.key' % userid)


def set_trust_cookie(response, userid):
	# Save a cookie for 30 days to skip two-step protection on this device
	# We save the username (so as to prevent stealing 2-step bypass cookies from other users)
	# and we use itsdangerous, using the app SECRET_KEY, to sign the cookie so we can verify
	# this instance of bargate actually set this two-step bypass cookie. We use timestamps
	# so the max time can be set at 30 days (during decode/design). That way we're not relying
	# on the browser deleting the cookie after 30 days - we enforce a max age server side.
	trust_signer = TimestampSigner(app.config['SECRET_KEY'], digest_method=hashlib.sha512)
	trust_token = trust_signer.sign(userid)
	response.set_cookie('2step', trust_token, expires=datetime.now() + timedelta(30))
	return response


def device_trusted(userid):
	trusted_cookie = request.cookies.get('2step', None)

	if trusted_cookie is not None:
		cookie_unsigner = TimestampSigner(app.config['SECRET_KEY'], digest_method=hashlib.sha512)
		try:
			# max age of the trusted device cookie is 30 days
			# 30 multplied by the number of seconds in a day (86400) = 2592000
			decoded = cookie_unsigner.unsign(trusted_cookie, max_age=2592000)
			if userid == decoded:
				return True
		except BadData as ex:
			app.logger.debug("trusted_device check for " + userid + " failed - unsign raised exception: " + str(ex))
			pass

	return False
