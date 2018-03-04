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

import urllib

import smbc
from flask import session, current_app as app

from bargate.lib import user


class SMBClient:
	"""the pysmbc library expects URL quoted str objects (as in, Python 2.x
	strings, rather than unicode strings. This wrapper class takes unicode
	non-quoted arguments and then silently converts the inputs into urllib
	quoted str objects instead, making use of the library a lot easier"""

	def __init__(self):
		self.smbclient = smbc.Context(auth_fn=self._get_auth)

	def _get_auth(self, server, share, workgroup, username, password):
		return (app.config['SMB_WORKGROUP'], session['username'], user.get_password())

	def _convert(self, url):
		# input will be of the form smb://location.location/path/path/path
		# we need to only URL quote the path, we must not quote the rest

		if not url.startswith("smb://"):
			raise Exception("URL must start with smb://")

		url = url.replace("smb://", "")
		(server, sep, path) = url.partition('/')

		if isinstance(url, str):
			return "smb://" + server.encode('utf-8') + "/" + urllib.quote(path)
		elif isinstance(url, unicode):
			return "smb://" + server + "/" + urllib.quote(path.encode('utf-8'))
		else:
			# uh.. hope for the best?
			return "smb://" + url

	def stat(self, url):
		if url.endswith('/'):
			url = url[:-1]

		url = self._convert(url)
		app.logger.debug("smbclient call: stat('" + url + "')")
		return self.smbclient.stat(url)

	def open(self, url, mode=None):
		url = self._convert(url)

		if mode is None:
			app.logger.debug("smbclient call: open('" + url + "')")
			return self.smbclient.open(url)
		else:
			app.logger.debug("smbclient call: open('" + url + "','" + str(mode) + "')")
			return self.smbclient.open(url, mode)

	def ls(self, url):
		url = self._convert(url)
		app.logger.debug("smbclient call: opendir('" + url + "').getdents()")
		return self.smbclient.opendir(url).getdents()

	def rename(self, old, new):
		old = self._convert(old)
		new = self._convert(new)
		app.logger.debug("smbclient call: rename('" + old + "','" + new + "')")
		self.smbclient.rename(old, new)

	def mkdir(self, url, mode=0755):
		url = self._convert(url)
		app.logger.debug("smbclient call: mkdir('" + url + "','" + str(mode) + "')")
		self.smbclient.mkdir(url, mode)

	def rmdir(self, url):
		url = self._convert(url)
		app.logger.debug("smbclient call: rmdir('" + url + "')")
		self.smbclient.rmdir(url)

	def delete(self, url):
		url = self._convert(url)
		app.logger.debug("smbclient call: unlink('" + url + "')")
		self.smbclient.unlink(url)

	def getxattr(self, url, attr):
		url = self._convert(url)
		app.logger.debug("smbclient call: getxattr('" + url + "','" + str(attr) + "')")
		return self.smbclient.getxattr(url, attr)
