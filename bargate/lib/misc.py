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

import datetime
import zlib
import json
import uuid
from base64 import b64decode

from itsdangerous import base64_decode
from flask import Markup
from werkzeug.http import parse_date


def ut_to_string(ut):
	"""Converts unix time to a formatted string for human consumption
	Used by smblib for turning fstat results into human readable dates.
	"""
	return datetime.datetime.fromtimestamp(int(ut)).strftime('%Y-%m-%d %H:%M:%S')


# Cookie decode for portal login
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
