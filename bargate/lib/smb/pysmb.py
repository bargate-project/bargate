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

import StringIO   # used in image previews
import socket     # used to get the local hostname to send to the SMB server
import tempfile   # used for reading from files on the smb server
import time       # used in search (timeout)
import errno      # used in OperationFailureDecode

from smb.SMBConnection import SMBConnection
from smb.base import SMBTimeout, NotReadyError, NotConnectedError, SharedDevice
from smb.smb_structs import UnsupportedFeature, ProtocolError, OperationFailure
from smb.smb_structs import SMBMessage
from smb.smb2_structs import SMB2Message
from flask import send_file, request, session, abort, make_response, jsonify
from PIL import Image

from bargate import app
from bargate.lib.core import banned_file, secure_filename, check_name, ut_to_string, wb_sid_to_name, EntryType
from bargate.lib.user import get_password
from bargate.lib.userdata import get_show_hidden_files, get_overwrite_on_upload, set_bookmark
from bargate.lib.mime import filename_to_mimetype, mimetype_to_icon, view_in_browser, pillow_supported
from bargate.lib.smb.base import LibraryBase
from bargate.lib.errors import stderr


class OperationFailureDecode:
	errmap = {
		0xC000000F: (errno.ENOENT, "STATUS_NO_SUCH_FILE"),
		0xC000000E: (errno.ENOENT, "STATUS_NO_SUCH_DEVICE"),
		0xC0000034: (errno.ENOENT, "STATUS_OBJECT_NAME_NOT_FOUND"),
		0xC0000039: (errno.ENOENT, "STATUS_OBJECT_PATH_INVALID"),
		0xC000003A: (errno.ENOENT, "STATUS_OBJECT_PATH_NOT_FOUND"),
		0xC000003B: (errno.ENOENT, "STATUS_OBJECT_PATH_SYNTAX_BAD"),
		0xC000009B: (errno.ENOENT, "STATUS_DFS_EXIT_PATH_FOUND"),
		0xC00000FB: (errno.ENOENT, "STATUS_REDIRECTOR_NOT_STARTED"),
		0xC00000CC: (errno.ENOENT, "STATUS_BAD_NETWORK_NAME"),
		0xC0000022: (errno.EPERM, "STATUS_ACCESS_DENIED"),
		0xC000001E: (errno.EPERM, "STATUS_INVALID_LOCK_SEQUENCE"),
		0xC000001F: (errno.EPERM, "STATUS_INVALID_VIEW_SIZE"),
		0xC0000021: (errno.EPERM, "STATUS_ALREADY_COMMITTED"),
		0xC0000041: (errno.EPERM, "STATUS_PORT_CONNETION_REFUSED"),
		0xC000004B: (errno.EPERM, "STATUS_THREAD_IS_TERMINATING"),
		0xC0000056: (errno.EPERM, "STATUS_DELETE_PENDING"),
		0xC0000061: (errno.EPERM, "STATUS_PRIVILEGE_NOT_HELD"),
		0xC000006D: (errno.EPERM, "STATUS_STATUS_LOGON_FAILURE"),
		0xC00000D5: (errno.EPERM, "STATUS_FILE_RENAMED"),
		0xC000010A: (errno.EPERM, "STATUS_PROCESS_IS_TERMINATING"),
		0xC0000121: (errno.EPERM, "STATUS_CANNOT_DELETE"),
		0xC0000123: (errno.EPERM, "STATUS_FILE_DELETED"),
		0xC00000CA: (errno.EPERM, "STATUS_NETWORK_ACCESS_DENIED"),
		0xC0000101: (errno.ENOTEMPTY, "STATUS_DIRECTORY_NOT_EMPTY"),
		0xC00000BA: (errno.EISDIR, "STATUS_FILE_IS_A_DIRECTORY"),
		0xC0000035: (errno.EEXIST, "STATUS_OBJECT_NAME_COLLISION"),
		0xC000007F: (errno.ENOSPC, "STATUS_DISK_FULL"),
	}

	def __init__(self, ex):
		self.err      = None
		self.code     = None
		self.ntstatus = None

		try:

			if hasattr(ex, 'smb_messages'):
				for msg in ex.smb_messages:
					if isinstance(msg, SMBMessage):
						code = msg.status.internal_value
					elif isinstance(msg, SMB2Message):
						code = msg.status

					if code == 0:
						continue  # first message code is always 0
					else:
						self.code = code

						if code in self.errmap.keys():
							(self.err, self.ntstatus) = self.errmap[code]
		except Exception:
			pass


class BargateSMBLibrary(LibraryBase):
	def smb_auth(self, username, password):
		self._init_paths(app.config['SMB_AUTH_URI'])

		try:
			conn = SMBConnection(username, password, socket.gethostname(), self.server_name,
				domain=app.config['SMB_WORKGROUP'], use_ntlm_v2=True, is_direct_tcp=True)
			if not conn.connect(self.server_name, port=445, timeout=10):
				app.logger.debug("smb_auth did not connect")
				return False
			conn.listPath(self.share_name, self.path_without_share)
			return True
		except Exception as ex:
			app.logger.debug("smb_auth exception: " + str(ex))
			return False

	def decode_exception(self, ex):
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

			return ("Operation failed", "The current operation failed")

		else:
			return ("Unknown error", "An unknown error occured")

	def _init_paths(self, endpoint_path, path=""):
		if endpoint_path.endswith('/'):
			endpoint_path = endpoint_path[:-1]

		# work out just the server name part of the URL
		epath_parts = endpoint_path.replace("smb://", "").split('/')
		self.server_name = epath_parts[0]

		if len(epath_parts) == 1:
			# there is no share in the uri
			if len(path) == 0:
				self.share_name = None
				self.path_without_share = u''
			else:
				(self.share_name, seperator, self.path_without_share) = path.partition('/')
		else:
			self.share_name = epath_parts[1]

			# is there multiple parts to the uri, i.e., we've not been
			# given a share root?
			if len(epath_parts) == 2:
				epath_without_share = u''
			else:
				epath_without_share = u"/" + u"/".join(epath_parts[2:])

			if len(epath_without_share) > 0:
				self.path_without_share = epath_without_share + u'/' + path
			else:
				self.path_without_share = path

		app.logger.debug('smblib._init_paths: share name: ' + unicode(self.share_name))
		app.logger.debug('smblib._init_paths: path without share: ' + unicode(self.path_without_share))

	def smb_action(self, endpoint_name, action, path):
		app.logger.debug("smb_action('" + endpoint_name + "','" + action + "','" + path + "')")

		self.smb_connection_init(endpoint_name, action, path)
		self._init_paths(self.endpoint_path, self.path)

		self.conn = SMBConnection(session['username'], get_password(), socket.gethostname(), self.server_name,
			domain=app.config['SMB_WORKGROUP'], use_ntlm_v2=True, is_direct_tcp=True)

		if not self.conn.connect(self.server_name, port=445, timeout=5):
			return stderr("Could not connect", "Could not connect to the file server, authentication was unsuccessful")

		return self.action_dispatch()

	def _action_download(self, view=False):
		app.logger.debug("_action_download()")

		try:
			# Default to sending files as an 'attachment' ("Content-Disposition: attachment")
			attach = True

			try:
				sfile = self.conn.getAttributes(self.share_name, self.path_without_share)
			except Exception as ex:
				return self.smb_error(ex)

			if sfile.isDirectory:
				abort(400)

			# guess a mimetype
			(ftype, mtype) = filename_to_mimetype(self.entry_name)

			# If the user requested to 'view' (don't download as an attachment)
			# make sure we allow it for that filetype
			if view:
				if view_in_browser(mtype):
					attach = False

			# pysmb wants to write to a file, rather than provide a file-like object to read from. EUGH.
			# so we need to write to a temporary file that Flask's send_file can then read from.
			tfile = tempfile.SpooledTemporaryFile(max_size=1048576)

			# Read data into the tempfile via SMB
			self.conn.retrieveFile(self.share_name, self.path_without_share, tfile)
			# Seek back to 0 on the tempfile, otherwise send_file breaks (!)
			tfile.seek(0)

			# Send the file to the user
			resp = make_response(send_file(tfile, add_etags=False, as_attachment=attach,
				attachment_filename=self.entry_name, mimetype=mtype))
			resp.headers['Content-length'] = sfile.file_size
			return resp

		except Exception as ex:
			return self.smb_error(ex)

	def _action_preview(self):
		app.logger.debug("_action_image_preview()")

		if not app.config['IMAGE_PREVIEW']:
			abort(400)

		try:
			sfile = self.conn.getAttributes(self.share_name, self.path_without_share)
		except Exception:
			abort(400)

		# ensure item is a file
		if sfile.isDirectory:
			abort(400)

		# guess a mimetype
		(ftype, mtype) = filename_to_mimetype(self.entry_name)

		# Check size is not too large for a preview
		if sfile.file_size > app.config['IMAGE_PREVIEW_MAX_SIZE']:
			abort(403)

		# Only preview files that Pillow supports
		if mtype not in pillow_supported:
			abort(400)

		try:
			# read the file
			tfile = tempfile.SpooledTemporaryFile(max_size=1048576)
			self.conn.retrieveFile(self.share_name, self.path_without_share, tfile)
			tfile.seek(0)

			pil_img = Image.open(tfile).convert('RGB')
			pil_img.thumbnail((app.config['IMAGE_PREVIEW_WIDTH'], app.config['IMAGE_PREVIEW_HEIGHT']))

			ifile = StringIO.StringIO()
			pil_img.save(ifile, 'PNG', compress_level=app.config['IMAGE_PREVIEW_LEVEL'])
			ifile.seek(0)
			return send_file(ifile, mimetype='image/png', add_etags=False)
		except Exception:
			abort(400)

	def _action_stat(self):
		app.logger.debug("_action_stat()")

		try:
			sfile = self.conn.getAttributes(self.share_name, self.path_without_share)
		except Exception as ex:
			return self.smb_error_json(ex)

		# ensure item is a file
		if sfile.isDirectory:
			return jsonify({'code': 1, 'msg': 'You cannot stat a directory!'})

		# guess mimetype
		(ftype, mtype) = filename_to_mimetype(sfile.filename)

		data = {
			'code': 0,
			'filename': sfile.filename,
			'size': sfile.file_size,
			'atime': ut_to_string(sfile.last_access_time),
			'mtime': ut_to_string(sfile.last_write_time),
			'ftype': ftype,
			'mtype': mtype,
			'owner': "N/A",
			'group': "N/A",
		}

		try:
			secDesc = self.conn.getSecurity(self.share_name, self.path_without_share)

			if app.config['WBINFO_LOOKUP']:
				data['owner'] = wb_sid_to_name(str(secDesc.owner))
				data['group'] = wb_sid_to_name(str(secDesc.group))
			else:
				data['owner'] = str(secDesc.owner)
				data['group'] = str(secDesc.group)
		except Exception as ex:
			pass

		return jsonify(data)

	def _action_search(self):
		app.logger.debug("_action_seach()")

		try:
			if not app.config['SEARCH_ENABLED']:
				return jsonify({'code': 1,
					'msg': "Search is not enabled"})

			# Build a breadcrumbs trail #
			crumbs = []
			parts  = self.path.split('/')
			b4     = ''

			# Build up a list of dicts, each dict representing a crumb
			for crumb in parts:
				if len(crumb) > 0:
					crumbs.append({'name': crumb, 'path': b4 + crumb})
					b4 = b4 + crumb + '/'

			parent     = False
			parent_path = None
			if len(crumbs) > 1:
				parent     = True
				parent_path = crumbs[-2]['path']
			elif len(crumbs) == 1:
				parent = True
				parent_path = ''

			query = request.args.get('q')
			results, timeout_reached = self._search(query)

			return jsonify({'code': 0,
				'results': results,
				'query': query,
				'crumbs': crumbs,
				'root_name': self.endpoint_title,
				'epname': self.endpoint_name,
				'epurl': self.endpoint_url,
				'path': self.path,
				'timeout_reached': timeout_reached,
				'parent': parent,
				'parent_path': parent_path})

		except Exception as ex:
			return jsonify({'code': 1, 'msg': str(type(ex)) + ": " + str(ex)})

	def _action_ls(self):
		app.logger.debug("_action_ls()")

		if self.share_name is None:
			try:
				smb_shares = self.conn.listShares()
			except Exception as ex:
				return self.smb_error_json(ex)

			shares = []
			for share in smb_shares:
				if share.type == SharedDevice.DISK_TREE:
					shares.append({'name': share.name})

			# are there any items in the list?
			no_items = False
			if len(shares) == 0:
				no_items = True

			return jsonify({'code': 0,
				'dirs': [],
				'files': [],
				'shares': shares,
				'crumbs': [],
				'buttons': False,
				'bmark': False,
				'root_name': self.endpoint_title,
				'epname': self.endpoint_name,
				'epurl': self.endpoint_url,
				'path': '',
				'no_items': no_items,
				'parent': False,
				'parent_path': None})

		else:
			try:
				try:
					directory_entries = self.conn.listPath(self.share_name, self.path_without_share)
				except Exception as ex:
					return self.smb_error_json(ex)

				# Seperate out dirs and files into two lists
				dirs  = []
				files = []

				# sfile = shared file (smb.base.SharedFile)
				for sfile in directory_entries:
					entry = self._sfile_load(sfile, self.path)

					# Don't add hidden files
					if not entry['skip']:
						etype = entry['type']
						entry.pop('skip', None)
						entry.pop('type', None)

						if etype == EntryType.file:
							files.append(entry)
						elif etype == EntryType.dir:
							dirs.append(entry)

				# Build a breadcrumbs trail #
				crumbs = []
				parts  = self.path.split('/')
				b4     = ''

				# Build up a list of dicts, each dict representing a crumb
				for crumb in parts:
					if len(crumb) > 0:
						crumbs.append({'name': crumb, 'path': b4 + crumb})
						b4 = b4 + crumb + '/'

				parent      = False
				parent_path = None
				if len(crumbs) > 1:
					parent     = True
					parent_path = crumbs[-2]['path']
				elif len(crumbs) == 1:
					parent = True
					parent_path = ''

				# are there any items in the list?
				no_items = False
				if len(files) == 0 and len(dirs) == 0:
					no_items = True

				# Don't allow bookmarks at the root of a function
				bmark_enabled = False
				if len(self.path) > 0:
					bmark_enabled = True

				return jsonify({'code': 0,
					'dirs': dirs,
					'files': files,
					'shares': [],
					'crumbs': crumbs,
					'buttons': True,
					'bmark_path': self.path + ' in ' + self.endpoint_title,
					'bmark': bmark_enabled,
					'root_name': self.endpoint_title,
					'epname': self.endpoint_name,
					'epurl': self.endpoint_url,
					'path': self.path,
					'no_items': no_items,
					'parent': parent,
					'parent_path': parent_path})

			except Exception as ex:
				return jsonify({'code': 1, 'msg': str(type(ex)) + ": " + str(ex)})

	def _action_upload(self):
		app.logger.debug("_action_upload()")

		ret = []

		uploaded_files = request.files.getlist("files[]")

		for ufile in uploaded_files:

			if banned_file(ufile.filename):
				ret.append({'name': ufile.filename, 'error': 'File type not allowed'})
				continue

			# Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
			filename = secure_filename(ufile.filename)
			upload_path = self.path_without_share + '/' + filename

			# Check the new file name is valid
			try:
				check_name(filename)
			except ValueError:
				ret.append({'name': ufile.filename, 'error': 'Filename not allowed'})
				continue

			file_already_exists = False
			try:
				sfile = self.conn.getAttributes(self.share_name, upload_path)
				file_already_exists = True
			except OperationFailure as ex:
				doesnotexist = False
				failure = OperationFailureDecode(ex)
				if failure.err is not None:
					if failure.err is errno.ENOENT:
						doesnotexist = True

				if not doesnotexist:
					(title, msg) = self.smb_error_info(ex)
					ret.append({'name': ufile.filename,
						'error': 'Could not check if file already exists: ' + title + " - " + msg})
					continue

			except Exception as ex:
				(title, msg) = self.smb_error_info(ex)
				ret.append({'name': ufile.filename,
					'error': 'Could not check if file already exists: ' + title + " - " + msg})
				continue

			byterange_start = 0
			if 'Content-Range' in request.headers:
				byterange_start = int(request.headers['Content-Range'].split(' ')[1].split('-')[0])

			# Check if we're writing from the start of the file
			if byterange_start == 0:
				# We're truncating an existing file, or creating a new file
				# If the file already exists, check to see if we should overwrite
				if file_already_exists:
					if not get_overwrite_on_upload():
						ret.append({'name': ufile.filename,
							'error': 'File already exists. You can enable overwriting files in Settings.'})
						continue

					# Now ensure we're not trying to upload a file on top of a directory (can't do that!)
					if sfile.isDirectory:
						ret.append({'name': ufile.filename,
							'error': "That name already exists and is a directory"})
						continue

			# Upload
			try:
				if byterange_start == 0:
					self.conn.storeFile(self.share_name, upload_path, ufile, timeout=120)
				else:
					self.conn.storeFileFromOffset(self.share_name, upload_path, ufile, offset=byterange_start)

				ret.append({'name': ufile.filename})
			except Exception as ex:
				(title, msg) = self.smb_error_info(ex)
				ret.append({'name': ufile.filename, 'error': title + ": " + msg})
				continue

		return jsonify({'files': ret})

	def _action_rename(self):
		app.logger.debug("_action_rename()")

		try:
			old_name = request.form['old_name']
			new_name = request.form['new_name']
		except Exception as ex:
			return jsonify({'code': 1, 'msg': 'Invalid parameter(s)'})

		# Check the new file name is valid
		try:
			check_name(new_name)
		except ValueError:
			return jsonify({'code': 1, 'msg': 'The new name is invalid'})

		# Build paths
		old_path = self.path_without_share + "/" + old_name
		new_path = self.path_without_share + "/" + new_name

		# Check existing file/directory exists
		try:
			sfile = self.conn.getAttributes(self.share_name, old_path)
		except Exception as ex:
			return self.smb_error_json(ex)

		if sfile.isDirectory:
			typestr = "directory"
		else:
			typestr = "file"

		try:
			self.conn.rename(self.share_name, old_path, new_path)
		except Exception as ex:
			return self.smb_error_json(ex)
		else:
			return jsonify({'code': 0, 'msg':
				"The " + typestr + " '" + old_name + "' was renamed to '" + new_name + "' successfully"})

	def _action_copy(self):
		app.logger.debug("_action_copy()")

		try:
			src  = request.form['src']
			dest = request.form['dest']
		except Exception as ex:
			return jsonify({'code': 1, 'msg': 'Invalid parameter(s)'})

		# check the proposed new name is valid
		try:
			check_name(dest)
		except ValueError:
			return jsonify({'code': 1, 'msg': 'The new name is invalid'})

		# Build paths
		src_path  = self.path_without_share + "/" + src
		dest_path = self.path_without_share + "/" + dest

		app.logger.debug("asked to copy from " + src + " to " + dest)

		# Check if existing file exists
		try:
			sfile = self.conn.getAttributes(self.share_name, src_path)
		except Exception as ex:
			return self.smb_error_json(ex)

		if sfile.isDirectory:
			return jsonify({'code': 1, 'msg': 'Unable to copy a directory!'})

		# Make sure the new file does not exist
		try:
			sfile = self.conn.getAttributes(self.share_name, dest_path)
			return jsonify({'code': 1, 'msg': 'The destination filename already exists'})
		except Exception as ex:
			# could not get attributes, so file probably does not exist, so lets continue
			pass

		# read into a local temp file, because you can't 'open' a file handle
		# in pysmb, you have to read the entire thing and store it somewhere
		# oh and we need to reset the file pos 'cos storeFile expects that
		try:
			tfile = tempfile.SpooledTemporaryFile(max_size=1048576)
			self.conn.retrieveFile(self.share_name, src_path, tfile)
			tfile.seek(0)
		except Exception as ex:
			return self.smb_error_json(ex)

		try:
			self.conn.storeFile(self.share_name, dest_path, tfile, timeout=120)
		except Exception as ex:
			return self.smb_error_json(ex)

		return jsonify({'code': 0, 'msg': 'A copy of "' + src + '" was created as "' + dest + '"'})

	def _action_mkdir(self):
		app.logger.debug("_action_mkdir()")

		try:
			dirname = request.form['name']
		except Exception as ex:
			return jsonify({'code': 1, 'msg': 'Invalid parameter'})

		# check the proposed new name is valid
		try:
			check_name(dirname)
		except ValueError:
			return jsonify({'code': 1, 'msg': 'The specified directory name is invalid'})

		try:
			self.conn.createDirectory(self.share_name, self.path_without_share + "/" + dirname)
		except Exception as ex:
			return self.smb_error_json(ex)

		return jsonify({'code': 0, 'msg': "The folder '" + dirname + "' was created successfully."})

	def _action_delete(self):
		app.logger.debug("_action_delete()")

		try:
			delete_name = request.form['name']
		except Exception as ex:
			return jsonify({'code': 1, 'msg': 'Invalid parameter'})

		delete_path  = self.path_without_share + "/" + delete_name

		try:
			sfile = self.conn.getAttributes(self.share_name, delete_path)
		except Exception as ex:
			return self.smb_error_json(ex)

		if sfile.isDirectory:
			try:
				self.conn.deleteDirectory(self.share_name, delete_path)
			except Exception as ex:
				return self.smb_error_json(ex)

			return jsonify({'code': 0, 'msg': "The directory '" + delete_name + "' was deleted"})

		else:
			try:
				self.conn.deleteFiles(self.share_name, delete_path)
			except Exception as ex:
				return self.smb_error_json(ex)

			return jsonify({'code': 0, 'msg': "The file '" + delete_name + "' was deleted"})

	def _action_bookmark(self):
		app.logger.debug("_action_bookmark()")

		try:
			bookmark_name = request.form['name']
		except Exception:
			return jsonify({'code': 1, 'msg': 'Invalid parameter'})

		set_bookmark(bookmark_name, self.endpoint_name, self.path)

	def _search(self, query):
		self.query           = query
		self.timeout_reached = False
		self.results         = []

		self.timeout_at = int(time.time()) + app.config['SEARCH_TIMEOUT']
		self._rsearch(self.path, self.path_without_share)
		return self.results, self.timeout_reached

	def _rsearch(self, path, path_without_share):
		app.logger.debug("rsearch " + path + " , " + path_without_share)
		try:
			directory_entries = self.conn.listPath(self.share_name, path_without_share)
		except Exception as ex:
			app.logger.debug("Search encountered an exception " + str(ex) + " " + str(type(ex)))
			return

		for sfile in directory_entries:
			# don't keep searching if we reach the timeout
			if self.timeout_reached:
				break
			elif int(time.time()) >= self.timeout_at:
				self.timeout_reached = True
				break

			entry = self._sfile_load(sfile, path)

			# Skip hidden files
			if entry['skip']:
				continue

			if self.query.lower() in entry['name'].lower():
				entry['parent_path'] = path
				self.results.append(entry)

			# Search subdirectories if we found one
			if entry['type'] == EntryType.dir:
				if len(path) > 0:
					sub_path = path + "/" + entry['name']
				else:
					sub_path = entry['name']

				if len(path_without_share) > 0:
					sub_path_without_share = path_without_share + "/" + entry['name']
				else:
					sub_path_without_share = entry['name']

				self._rsearch(sub_path, sub_path_without_share)

	def _sfile_load(self, sfile, path):
		"""Takes a smb SharedFile object and returns a dictionary with information
		about that SharedFile object.
		"""
		entry = {'skip': False, 'name': sfile.filename, 'epurl': self.endpoint_url}

		if len(path) == 0:
			entry['path'] = entry['name']
		else:
			entry['path'] = path + '/' + entry['name']

		# Skip entries for 'this dir' and 'parent dir'
		if entry['name'] == '.' or entry['name'] == '..':
			entry['skip'] = True
			return entry

		# hidden files
		if not get_show_hidden_files():
			if entry['name'].startswith('.'):
				entry['skip'] = True
			if entry['name'].startswith('~$'):
				entry['skip'] = True
			if entry['name'] in ['desktop.ini', '$RECYCLE.BIN', 'RECYCLER', 'Thumbs.db']:
				entry['skip'] = True

		if entry['skip']:
			return entry

		# Directories
		if sfile.isDirectory:
			entry['type'] = EntryType.dir

		# Files
		else:
			entry['type'] = EntryType.file
			entry['size'] = sfile.file_size

			# Generate 'mtype', 'mtyper' and 'icon'
			entry['icon'] = 'file-text-o'
			(entry['mtype'], entry['mtyper']) = filename_to_mimetype(entry['name'])
			entry['icon'] = mimetype_to_icon(entry['mtyper'])

			# modification time (last write)
			entry['mtimer'] = sfile.last_write_time
			entry['mtime']     = ut_to_string(sfile.last_write_time)

			# Image previews
			if app.config['IMAGE_PREVIEW'] and entry['mtyper'] in pillow_supported:
				if int(entry['size']) <= app.config['IMAGE_PREVIEW_MAX_SIZE']:
					entry['img'] = True

			# View-in-browser download type
			if view_in_browser(entry['mtyper']):
				entry['view'] = True

		return entry
