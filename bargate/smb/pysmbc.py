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
import io
import stat
import time
import tempfile

import smbc
from flask import current_app as app

from bargate.lib import fs
from bargate.smb import LibraryBase, Entry, FatalError, NotFoundError
from bargate.smb.libsmbclient import SMBClient


class EntryData(Entry):
	def __init__(self, name, fstat):

		self.size  = fstat[6]
		self.atime = fstat[7]
		self.mtime = fstat[8]
		self.ctime = fstat[9]

		if stat.S_ISDIR(fstat[0]):
			self.type = fs.TYPE_DIR
		elif stat.S_ISREG(fstat[0]):
			self.type = fs.TYPE_FILE
		else:
			self.type = fs.TYPE_OTHER

		# old versions of pysmbc returned str rather than unicode
		if isinstance(name, str):
			name = name.decode("utf-8")

		super(EntryData, self).__init__(name)


class BargateSMBLibrary(LibraryBase):
	def prepare(self):
		if not self.endpoint_path.endswith('/'):
			self.endpoint_path = self.endpoint_path + '/'

		# All requests to the SMB library need to include the addr (defined in shares.conf)
		# and the path the user has navigated to, combined.
		self.addr = self.endpoint_path + self.path
		if self.addr.endswith('/'):
			self.addr = self.addr[:-1]

	def smb_auth(self, username, password):
		"""Tries to 'authenticate' the user/pass by conneting to a remote share and listing contents"""

		try:
			cb = lambda se, sh, w, u, p: (app.config['SMB_WORKGROUP'], username, password)  # noqa
			ctx = smbc.Context(auth_fn=cb)
			ctx.opendir(app.config['SMB_AUTH_URI']).getdents()
		except smbc.PermissionError:
			app.logger.debug("bargate.lib.user.auth smb permission denied")
			return False
		except Exception as ex:
			app.logger.debug("bargate.lib.user.auth smb exception: " + str(ex))
			return False

		return True
		app.logger.debug("bargate.lib.user.auth auth smb success")

	def decode_exception(self, ex):
		"""Determine a human friendly title and description based on the exception passed"""

		if isinstance(ex, smbc.PermissionError):
			return ("Permission Denied", "You do not have permission to perform the action")

		elif isinstance(ex, smbc.NoEntryError):
			return ("No such file or directory", "The file or directory was not found")

		elif isinstance(ex, smbc.NoSpaceError):
			return ("No space left on device", "There is no space left on the server, or you have exceeded your quota")

		elif isinstance(ex, smbc.ExistsError):
			if self.action == 'ls':
				return ("Not found", "The directory specified does not exist")
			else:
				return ("Name already exists", "The file or directory you attempted to create already exists")

		elif isinstance(ex, smbc.NotEmptyError):
			return ("The directory is not empty", "The directory is not empty so cannot be deleted")

		elif isinstance(ex, smbc.TimedOutError):
			return ("Timed out", "The current operation timed out. Please try again later")

		elif isinstance(ex, smbc.ConnectionRefusedError):
			return self.smbc_ConnectionRefusedError()

		# pysmbc spits out RuntimeError when everything else fails
		elif isinstance(ex, RuntimeError):
			return ("File Server Error",
				"An unknown error was returned from the file server. Please contact your support team")

		# ALL OTHER EXCEPTIONS
		else:
			return ("Error", type(ex).__name__ + ": " + str(ex))

	def connect(self):
		self.libsmbclient = SMBClient()

	def ls(self):
		files  = []
		dirs   = []
		shares = []

		directory_entries = self.libsmbclient.ls(self.addr)

		for smbc_dirent in directory_entries:
			entry = self.stat(smbc_dirent.name).to_dict(self.path)

			if not entry['skip']:
				etype = entry['type']
				entry.pop('skip', None)
				entry.pop('type', None)

				if etype == fs.TYPE_FILE:
					files.append(entry)
				elif etype == fs.TYPE_DIR:
					dirs.append(entry)
				elif etype == fs.TYPE_SHARE:
					shares.append(entry)

		return (files, dirs, shares)

	def get_owner_group(self, name=None):
		path = self.addr
		if name is not None:
			path = path + "/" + name

		owner = self.libsmbclient.getxattr(path, smbc.XATTR_OWNER)
		group = self.libsmbclient.getxattr(path, smbc.XATTR_GROUP)

		return (owner, group)

	def get_spooled_fp(self, name=None):
		fp = self.get_fp(name)

		temp_file = tempfile.SpooledTemporaryFile(max_size=1048576)
		temp_file.write(fp.read())
		temp_file.seek(0)
		return temp_file

	def get_fp(self, name=None):
		path = self.addr
		if name is not None:
			path = path + "/" + name

		return self.libsmbclient.open(path)

	def upload(self, filename, fp, byterange_start=0):
		path = self.addr + "/" + filename

		if byterange_start == 0:
			wfile = self.libsmbclient.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
		else:
			wfile = self.libsmbclient.open(path, os.O_WRONLY)
			wfile.seek(byterange_start)

		while True:
			buff = fp.read(io.DEFAULT_BUFFER_SIZE)
			if not buff:
				break
			wfile.write(buff)

		wfile.close()

	def rename(self, old_name, new_name):
		old_path = self.addr + "/" + old_name
		new_path = self.addr + "/" + new_name
		self.libsmbclient.rename(old_path, new_path)

	def copy(self, src, dest, size):
		src_path  = self.addr + "/" + src
		dest_path = self.addr + "/" + dest

		src_fp  = self.libsmbclient.open(src_path)
		dest_fp = self.libsmbclient.open(dest_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)

		location = 0
		while(location >= 0 and location < size):
			chunk = src_fp.read(1024)
			dest_fp.write(chunk)
			location = src_fp.seek(1024, location)

	def mkdir(self, name):
		path  = self.addr + "/" + name
		self.libsmbclient.mkdir(path)

	def stat(self, name=None):
		if name is None:
			name = self.entry_name
			path = self.addr
		else:
			path = self.addr + "/" + name

		try:
			return EntryData(name, self.libsmbclient.stat(path))

		except smbc.NoEntryError:
			raise NotFoundError()

	def delete_file(self, name):
		path  = self.addr + "/" + name
		self.libsmbclient.delete(path)

	def delete_dir(self, name):
		path  = self.addr + "/" + name

		contents = self.libsmbclient.ls(path)
		contents = filter(lambda s: not (s.name == '.' or s.name == '..'), contents)
		if len(contents) > 0:
			raise FatalError("The directory is not empty")

		self.libsmbclient.rmdir(path)

	def _search(self, query):
		self.query           = query
		self.timeout_reached = False
		self.results         = []

		self.timeout_at = int(time.time()) + app.config['SEARCH_TIMEOUT']
		self._rsearch(self.path)
		return (self.results, self.timeout_reached)

	def _rsearch(self, path):
		# Try getting directory contents of where we are
		app.logger.debug("_rsearch called to search: " + path)
		try:
			directory_entries = self.libsmbclient.ls(self.addr + path)
		except smbc.NotDirectoryError as ex:
			return
		except Exception as ex:
			app.logger.info("Search encountered an exception " + type(ex).__name__ + ": " + str(ex))
			return

		# now loop over each entry
		for dentry in directory_entries:

			# don't keep searching if we reach the timeout
			if self.timeout_reached:
				break
			elif int(time.time()) >= self.timeout_at:
				self.timeout_reached = True
				break

			entry = self.stat(dentry.name).to_dict(path, include_path=True)

			# Skip hidden files
			if entry['skip']:
				continue

			# Check if the filename matched
			if self.query.lower() in entry['name'].lower():
				app.logger.debug("_rsearch: Matched: " + entry['name'])
				entry['parent_path'] = path
				self.results.append(entry)

			# Search subdirectories if we found one
			if entry['type'] == fs.TYPE_DIR:
				if len(path) > 0:
					sub_path = path + "/" + entry['name']
				else:
					sub_path = entry['name']

				self._rsearch(sub_path)
