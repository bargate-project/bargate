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

from cryptography.fernet import Fernet


def encrypt(data, key):
	if isinstance(data, unicode):
		data = data.encode('utf-8')

	if len(key) != 32:
		raise RuntimeError('The encryption key MUST be 32-characters long')

	key = base64.urlsafe_b64encode(key)
	return Fernet(key).encrypt(data)
	

def decrypt(data, key):
	key = base64.urlsafe_b64encode(key)
	return Fernet(key).decrypt(data)
