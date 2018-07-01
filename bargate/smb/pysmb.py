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

import socket
import tempfile
import errno
import traceback

from smb.SMBConnection import SMBConnection
from smb.base import SMBTimeout, NotReadyError, NotConnectedError, SharedDevice
from smb.smb_structs import UnsupportedFeature, ProtocolError, OperationFailure
from flask import session
from flask import current_app as app

from bargate.lib import fs, user, errors
from bargate.smb import LibraryBase, DirectoryEntry
from bargate.smb.pysmb_errors import OperationFailureDecode


class EntryData(DirectoryEntry):
	"""A wrapper class to provide a consistent interface to file information across backends"""

	def __init__(self, shared_file):

		self.size  = shared_file.file_size
		self.atime = shared_file.last_access_time
		self.mtime = shared_file.last_write_time
		self.ctime = shared_file.last_attr_change_time

		if shared_file.isDirectory:
			self.type = fs.TYPE_DIR
		else:
			self.type = fs.TYPE_FILE

		super(EntryData, self).__init__(shared_file.filename)


class BargateSMBLibrary(LibraryBase):
	def prepare(self):
		if self.endpoint_path.endswith('/'):
			self.endpoint_path = self.endpoint_path[:-1]

		# work out just the server name part of the URL
		epath_parts = self.endpoint_path.replace("smb://", "").split('/')
		self.server_name = epath_parts[0]

		if len(epath_parts) == 1:
			# there is no share in the uri
			if len(self.path) == 0:
				self.share_name = None
				self.path_without_share = u''
			else:
				(self.share_name, seperator, self.path_without_share) = self.path.partition('/')
		else:
			self.share_name = epath_parts[1]

			# is there multiple parts to the uri, i.e., we've not been given a share root?
			if len(epath_parts) == 2:
				epath_without_share = u''
			else:
				epath_without_share = u"/" + u"/".join(epath_parts[2:])

			if len(epath_without_share) > 0:
				self.path_without_share = epath_without_share + u'/' + self.path
			else:
				self.path_without_share = self.path

		app.logger.debug('pysmb.prepare: share name: ' + unicode(self.share_name))
		app.logger.debug('pysmb.prepare: path without share: ' + unicode(self.path_without_share))

	def smb_auth(self, username, password):
		"""Tries to 'authenticate' the user/pass by conneting to a remote share and listing contents"""

		self.endpoint_path = app.config['SMB_AUTH_URI']
		self.prepare()

		try:
			conn = SMBConnection(username, password, socket.gethostname(), self.server_name,
				domain=app.config['SMB_WORKGROUP'], use_ntlm_v2=True, is_direct_tcp=True)
			if not conn.connect(self.server_name, port=445, timeout=10):
				app.logger.debug("smb_auth did not connect")
				return False
			conn.listPath(self.share_name, self.path_without_share)
			return True
		except Exception as ex:
			app.logger.debug("smb_auth exception: " + str(type(ex).__name__) + " - " + str(ex))
			app.logger.debug(traceback.format_exc())
			return False

	def connect(self):
		self.conn = SMBConnection(session['username'], user.get_password(), socket.gethostname(), self.server_name,
			domain=app.config['SMB_WORKGROUP'], use_ntlm_v2=True, is_direct_tcp=True)

		if not self.conn.connect(self.server_name, port=445, timeout=5):
			raise errors.FatalError("Could not connect to the file server")

	def decode_exception(self, ex):
		"""Determine a human friendly title and description based on the exception passed"""

		# pysmb exceptions
		if isinstance(ex, SMBTimeout):
			return ("Timed out", "The current operation timed out. Please try again later")

		elif isinstance(ex, NotReadyError):
			return ("Server not ready", "Authentication has failed or not yet performed")

		elif isinstance(ex, NotConnectedError):
			return ("Connection closed", "The server closed the connection unexpectedly")

		elif isinstance(ex, UnsupportedFeature):
			return ("Unsupported SMB feature",
				"The server requires a later version of the SMB protocol than is supported")

		elif isinstance(ex, ProtocolError):
			return ("Protocol error", "The server sent a malformed response")

		elif isinstance(ex, OperationFailure):
			failure = OperationFailureDecode(ex)
			if failure.err is not None:
				if failure.err is errno.ENOENT:
					return ("No such entry", "The file or directory does not exist")
				elif failure.err is errno.EPERM:
					return ("Permission denied", "You do not have sufficient permission to complete the operation")
				elif failure.err is errno.ENOTEMPTY:
					return ("Directory not empty", "You can only delete empty directories.")
				elif failure.err is errno.EISDIR:
					return ("Entry is a directory", "You attempted to perform a file operation on a directory")
				elif failure.err is errno.EEXIST:
					return ("Entry already exists", "The file or directory already exists")
				elif failure.err is errno.ENOSPC:
					return ("No space left", "No space left on device. You may have exceeded your usage allowance.")
				elif failure.err is errno.EINVAL:
					return ("Invalid parameter", "The SMB server said: invalid parameter")

			return ("Operation failed", "The current operation failed")

		else:
			return ("Error", type(ex).__name__ + ": " + str(ex))

	def ls(self, path_suffix=None, strip_data=True):
		app.logger.debug("ls called with " + str(path_suffix))
		files  = []
		dirs   = []
		shares = []

		if path_suffix is None:
			if self.share_name is None:
				smb_shares = self.conn.listShares()
				for share in smb_shares:
					if share.type == SharedDevice.DISK_TREE:
						shares.append({'name': share.name})

				return (files, dirs, shares)
			else:
				ls_path = self.path
				ls_share_name = self.share_name
				ls_path_without_share = self.path_without_share
		else:
			if len(self.path) > 0:
				ls_path = self.path + '/' + path_suffix
			else:
				ls_path = path_suffix

			if self.share_name is None:
				parts = path_suffix.split('/')
				ls_share_name = parts[0]
				ls_path_without_share = '/'.join(parts[1:])
			else:
				ls_share_name = self.share_name
				if len(self.path_without_share) > 0:
					ls_path_without_share = self.path_without_share + '/' + path_suffix
				else:
					ls_path_without_share = path_suffix

		app.logger.debug("listPath " + ls_share_name + " -- " + ls_path_without_share)

		directory_entries = self.conn.listPath(ls_share_name, ls_path_without_share)

		for shared_file in directory_entries:
			entry = EntryData(shared_file).to_dict(ls_path)

			if not entry['skip']:
				etype = entry['type']
				if strip_data:
					entry.pop('skip', None)
					entry.pop('type', None)

				if etype == fs.TYPE_FILE:
					files.append(entry)
				elif etype == fs.TYPE_DIR:
					dirs.append(entry)

		return (files, dirs, shares)

	def get_spooled_fp(self, name=None):
		path = self.path_without_share
		if name is not None:
			path = path + "/" + name

		temp_file = tempfile.SpooledTemporaryFile(max_size=1048576)
		self.conn.retrieveFile(self.share_name, path, temp_file)
		temp_file.seek(0)
		return temp_file

	def get_fp(self, name=None):
		return self.get_spooled_fp(name)

	def upload(self, filename, fp, byterange_start=0):
		upload_path = self.path_without_share + '/' + filename

		if byterange_start == 0:
			self.conn.storeFile(self.share_name, upload_path, fp, timeout=120)
		else:
			self.conn.storeFileFromOffset(self.share_name, upload_path, fp, offset=byterange_start)

	def rename(self, old_name, new_name):
		old_path = self.path_without_share + "/" + old_name
		new_path = self.path_without_share + "/" + new_name
		self.conn.rename(self.share_name, old_path, new_path)

	def copy(self, src, dest, size):
		src_path  = self.path_without_share + "/" + src
		dest_path = self.path_without_share + "/" + dest

		# read into a local temp file, because you can't 'open' a file handle
		# in pysmb, you have to read the entire thing and store it somewhere (!)
		# oh and we need to reset the file pos 'cos storeFile expects that
		temp_file = tempfile.SpooledTemporaryFile(max_size=1048576)
		self.conn.retrieveFile(self.share_name, src_path, temp_file)
		temp_file.seek(0)
		self.conn.storeFile(self.share_name, dest_path, temp_file, timeout=120)

	def mkdir(self, name):
		path = self.path_without_share + "/" + name
		self.conn.createDirectory(self.share_name, path)

	def stat(self, name=None):
		path = self.path_without_share
		if name is not None:
			path = path + "/" + name

		try:
			shared_file = self.conn.getAttributes(self.share_name, path)
			return EntryData(shared_file)
		except OperationFailure as ex:
			failure = OperationFailureDecode(ex)
			if failure.err is not None:
				if failure.err is errno.ENOENT:
					raise errors.NotFoundError()

			raise ex

	def delete_file(self, name):
		path = self.path_without_share + "/" + name
		self.conn.deleteFiles(self.share_name, path)

	def delete_dir(self, name):
		path = self.path_without_share + "/" + name
		self.conn.deleteDirectory(self.share_name, path)
