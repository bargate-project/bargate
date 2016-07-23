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

from Crypto.Cipher import AES
import base64
import os
import bargate.lib.errors

################################################################################

def encrypt(s,key):
	"""This function is used to encrypt a string via AES.
	Pass it the string to encrypt and the key to use to do so.
	Returns a base64 encoded string using AES CFB.
	"""
	
	## https://www.dlitz.net/software/pycrypto/api/current/Crypto.Cipher.blockalgo-module.html#MODE_CFB
	## CFB does not require padding
	## 32-bit key is required (AES256)
	
	# Create the IV (Initialization Vector)
	iv = os.urandom(AES.block_size)
	
	## Create the cipher with the key, mode and iv
	c = AES.new(key,AES.MODE_CFB,iv)
	
	## Base 64 encode the iv and the encrypted data together
	b64 = base64.b64encode(iv + c.encrypt(s))
	
	## return the base64 encoded string
	return b64

################################################################################

def decrypt(s,key):
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
