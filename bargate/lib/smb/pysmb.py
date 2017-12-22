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

import StringIO  # used in image previews
import socket    # used to get the local hostname to send to the SMB server
import tempfile  # used for reading from files on the smb server
import time      # used in search (timeout)
import uuid      # used in creating bookmarks
import errno     # used in OperationFailureDecode

from smb.SMBConnection import SMBConnection
from smb.base import SMBTimeout, NotReadyError, NotConnectedError, SharedDevice
from smb.smb_structs import UnsupportedFeature, ProtocolError, OperationFailure
from smb.smb_structs import SMBMessage
from smb.smb2_structs import SMB2Message
from flask import send_file, request, session, g, url_for, abort
from flask import make_response, jsonify, render_template
from PIL import Image

from bargate import app
from bargate.lib.core import banned_file, secure_filename, check_name
from bargate.lib.core import ut_to_string, wb_sid_to_name, check_path
from bargate.lib.core import EntryType
from bargate.lib.errors import stderr, invalid_path
from bargate.lib.user import get_password
from bargate.lib.userdata import get_show_hidden_files
from bargate.lib.userdata import get_overwrite_on_upload
from bargate.lib.mime import filename_to_mimetype, mimetype_to_icon
from bargate.lib.mime import view_in_browser, pillow_supported


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


class BargateSMBLibrary:

	def smb_auth(self, username, password):
		server_name, share_name, path_without_share = self._parse_smb_uri_and_path(app.config['SMB_AUTH_URI'])

		try:
			conn = SMBConnection(username, password, socket.gethostname(), server_name,
				domain=app.config['SMB_WORKGROUP'], use_ntlm_v2=True, is_direct_tcp=True)
			if not conn.connect(server_name, port=445, timeout=10):
				app.logger.debug("smb_auth did not connect")
				return False
			conn.listPath(share_name, path_without_share)
			return True
		except Exception as ex:
			app.logger.debug("smb_auth exception: " + str(ex))
			return False

	def smb_error_info(self, ex):

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

	def smb_error(self, ex):
		(title, desc) = self.smb_error_info(ex)
		return stderr(title, desc)

	def smb_error_json(self, ex):
		(title, msg) = self.smb_error_info(ex)
		app.logger.debug("smb_error_json: '" + title + "', '" + msg + "'")
		app.logger.debug(traceback.format_exc())
		return jsonify({'code': 1, 'msg': title + ": " + msg})

	def _parse_smb_uri_and_path(self, uri, path=""):
		# work out just the server name part of the URL
		uri_parts   = uri.replace("smb://", "").split('/')
		server_name = uri_parts[0]

		if len(uri_parts) == 1:
			# there is no share in the uri
			if len(path) == 0:
				share_name = None
				path_without_share = ""
			else:
				(share_name, seperator, path_without_share) = path.partition('/')
		else:
			share_name = uri_parts[1]

			# is there multiple parts to the uri, i.e., we've not been
			# given a share root?
			if len(uri_parts) == 2:
				uri_without_share = ""
			else:
				uri_without_share = "/" + "/".join(uri_parts[2:])

			if len(uri_without_share) > 0:
				path_without_share = uri_without_share + "/" + path
			else:
				path_without_share = path

		return server_name, share_name, path_without_share

	def smb_action(self, func_path, func_name, active=None, display_name="Home", action='browse', path=''):
		"""
			func_path		this is the full SMB path to the server, optionally
							including the share name, and any subsequent dirs
							the user can't browse 'above' this path, and does
							not get to see this path.

			func_name		a unique identifier for this 'view' or 'function'
							that the user can select and use.

			active			what should the 'active' variable set to, for menu
							highlights in HTML?

			display_name	the friendly name for this 'view' or 'function',
							to use instead of the func_path. Defaults to "Home".

			action			the action the user is trying to perform

			path			the path the user is viewing, which is in addition
							to the 'func_path'.

			example:
				func_path		smb://server/users/username/
				func_name		userfiles
				active			userfiles
				display_name	my files
				action			browse
				path			mydocuments/
		"""

		# default the 'active' variable to the function name
		if active is None:
			active = func_name

		# If the method is POST then 'action' is sent via a POST parameter
		# rather than via a so-called "GET" parameter in the URL
		if request.method == 'POST':
			action = request.form['action']

		if func_path.endswith('/'):
			func_path = func_path[:-1]

		# func_path should always start with smb://
		if not func_path.startswith("smb://"):
			return stderr("Invalid server path", 'The server URL must start with smb://')

		# Work out the server_name, share name, and the path without the share name
		server_name, share_name, path_without_share = self._parse_smb_uri_and_path(func_path, path)

		# Work out the 'entry name'
		if len(path) > 0:
			(a, b, entry_name) = path.rpartition('/')
		else:
			entry_name = u""

		# Check the path is not bad/dangerous
		try:
			check_path(path)
		except ValueError:
			return invalid_path()

		# Connect to the SMB server
		conn = SMBConnection(session['username'], get_password(), socket.gethostname(), server_name,
			domain=app.config['SMB_WORKGROUP'], use_ntlm_v2=True, is_direct_tcp=True)

		if not conn.connect(server_name, port=445, timeout=5):
			return stderr("Could not connect", "Could not connect to the file server, authentication was unsuccessful")

		app.logger.info('user: "' + session['username'] + '", func_path: "' + func_path + '", share_name: "' +
			unicode(share_name) + '", endpoint: "' + func_name + '", action: "' + action + '", method: ' +
			str(request.method) + ', path: "' + path + '", addr: "' + request.remote_addr + '", ua: ' +
			request.user_agent.string)

		if share_name is None:
			# there is no share name specified, so the only thing we can do here is browse
			if action == 'browse':
				if 'xhr' in request.args:

					try:
						smb_shares = conn.listShares()
					except Exception as ex:
						return self.smb_error_json(ex)

					shares = []
					for share in smb_shares:
						if share.type == SharedDevice.DISK_TREE:
							shares.append({'name': share.name, 'burl': url_for(func_name)})

					# are there any items in the list?
					no_items = False
					if len(shares) == 0:
						no_items = True

					return jsonify({'dirs': [], 'files': [], 'shares': shares,
						'crumbs': [], 'buttons': False, 'bmark': False,
						'root_name': display_name, 'code': 0,
						'root_url': url_for(func_name), 'no_items': no_items})

				else:
					return render_template('browse.html', active=active,
						url=url_for(func_name, path=path), browse_mode=True)
			else:
				abort(400)

		if request.method == 'GET':
			# GET: DOWNLOAD OR 'VIEW' FILE
			if action == 'download' or action == 'view':

				try:
					# Default to sending files as an 'attachment' ("Content-Disposition: attachment")
					attach = True

					try:
						sfile = conn.getAttributes(share_name, path_without_share)
					except Exception as ex:
						return self.smb_error(ex)

					if sfile.isDirectory:
						abort(400)

					# guess a mimetype
					(ftype, mtype) = filename_to_mimetype(entry_name)

					# If the user requested to 'view' (don't download as an attachment)
					# make sure we allow it for that filetype
					if action == 'view':
						if view_in_browser(mtype):
							attach = False

					# pysmb wants to write to a file, rather than provide a file-like object to read from. EUGH.
					# so we need to write to a temporary file that Flask's send_file can then read from.
					tfile = tempfile.SpooledTemporaryFile(max_size=1048576)

					# Read data into the tempfile via SMB
					conn.retrieveFile(share_name, path_without_share, tfile)
					# Seek back to 0 on the tempfile, otherwise send_file breaks (!)
					tfile.seek(0)

					# Send the file to the user
					resp = make_response(send_file(tfile, add_etags=False, as_attachment=attach,
						attachment_filename=entry_name, mimetype=mtype))
					resp.headers['Content-length'] = sfile.file_size
					return resp

				except Exception as ex:
					return self.smb_error(ex)

			# GET: IMAGE PREVIEW
			elif action == 'preview':
				if not app.config['IMAGE_PREVIEW']:
					abort(400)

				try:
					sfile = conn.getAttributes(share_name, path_without_share)
				except Exception as ex:
					abort(400)

				# ensure item is a file
				if sfile.isDirectory:
					abort(400)

				# guess a mimetype
				(ftype, mtype) = filename_to_mimetype(entry_name)

				# Check size is not too large for a preview
				if sfile.file_size > app.config['IMAGE_PREVIEW_MAX_SIZE']:
					abort(403)

				# Only preview files that Pillow supports
				if mtype not in pillow_supported:
					abort(400)

				try:
					# read the file
					tfile = tempfile.SpooledTemporaryFile(max_size=1048576)
					conn.retrieveFile(share_name, path_without_share, tfile)
					tfile.seek(0)

					pil_img = Image.open(tfile).convert('RGB')
					size = 200, 200
					pil_img.thumbnail(size, Image.ANTIALIAS)

					ifile = StringIO.StringIO()
					pil_img.save(ifile, 'JPEG', quality=85)
					ifile.seek(0)
					return send_file(ifile, mimetype='image/jpeg', add_etags=False)
				except Exception as ex:
					abort(400)

			# GET: STAT FILE (ajax call to get more details)
			elif action == 'stat':

				try:
					sfile = conn.getAttributes(share_name, path_without_share)
				except Exception as ex:
					return self.smb_error_json(ex)

				# ensure item is a file
				if sfile.isDirectory:
					return jsonify({'code': 1, 'msg': 'You cannot stat a directory!'})

				# guess mimetype
				(ftype, mtype) = filename_to_mimetype(sfile.filename)

				data = {
					'filename': sfile.filename,
					'size': sfile.file_size,
					'atime': ut_to_string(sfile.last_access_time),
					'mtime': ut_to_string(sfile.last_write_time),
					'ftype': ftype,
					'mtype': mtype,
					'owner': "N/A",
					'group': "N/A",
					'code': 0,
				}

				try:
					secDesc = conn.getSecurity(share_name, path_without_share)

					if app.config['WBINFO_LOOKUP']:
						data['owner'] = wb_sid_to_name(str(secDesc.owner))
						data['group'] = wb_sid_to_name(str(secDesc.group))
					else:
						data['owner'] = str(secDesc.owner)
						data['group'] = str(secDesc.group)
				except Exception as ex:
					pass

				return jsonify(data)

			# GET: BROWSE
			elif action == 'browse':
				# SEARCH
				if 'q' in request.args:
					try:
						if not app.config['SEARCH_ENABLED']:
							return jsonify({'code': 1,
								'msg': "Search is not enabled"})

						# Build a breadcrumbs trail #
						crumbs = []
						parts = path.split('/')
						b4 = ''

						# Build up a list of dicts, each dict representing a crumb
						for crumb in parts:
							if len(crumb) > 0:
								crumbs.append({'name': crumb, 'url': url_for(func_name, path=b4 + crumb)})
								b4 = b4 + crumb + '/'

						query = request.args.get('q')
						self._init_search(conn, func_name, share_name, path, path_without_share, query)
						results, timeout_reached = self._search()

						return jsonify({'code': 0,
							'results': results,
							'query': query,
							'crumbs': crumbs,
							'root_name': display_name,
							'root_url': url_for(func_name),
							'timeout_reached': timeout_reached})
					except Exception as ex:
						return jsonify({'code': 1, 'msg': str(type(ex)) + ": " + str(ex)})

				elif 'xhr' in request.args:
					try:

						try:
							directory_entries = conn.listPath(share_name, path_without_share)
						except Exception as ex:
							return self.smb_error_json(ex)

						# Seperate out dirs and files into two lists
						dirs  = []
						files = []

						# sfile = shared file (smb.base.SharedFile)
						for sfile in directory_entries:
							entry = self._sfile_load(sfile, path, func_name)

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
						parts  = path.split('/')
						b4     = ''

						# Build up a list of dicts, each dict representing a crumb
						for crumb in parts:
							if len(crumb) > 0:
								crumbs.append({'name': crumb, 'url': url_for(func_name, path=b4 + crumb)})
								b4 = b4 + crumb + '/'

						# are there any items in the list?
						no_items = False
						if len(files) == 0 and len(dirs) == 0:
							no_items = True

						# Don't allow bookmarks at the root of a function
						# - that is superfluous
						bmark_enabled = False
						if len(path) > 0:
							bmark_enabled = True

						return jsonify({'dirs': dirs, 'files': files, 'shares': [],
							'crumbs': crumbs, 'buttons': True, 'bmark_path': path + ' in ' + display_name,
							'bmark': bmark_enabled, 'root_name': display_name,
							'root_url': url_for(func_name), 'no_items': no_items})

					except Exception as ex:
						return jsonify({'code': 1, 'msg': str(type(ex)) + ": " + str(ex)})

				else:
					return render_template('browse.html',
						active=active,
						path=path, browse_mode=True,
						url=url_for(func_name,
						path=path))

			else:
				abort(400)

		elif request.method == 'POST':
			# POST: UPLOAD
			if action == 'upload':
				ret = []

				uploaded_files = request.files.getlist("files[]")

				for ufile in uploaded_files:

					if banned_file(ufile.filename):
						ret.append({'name': ufile.filename, 'error': 'Filetype not allowed'})
						continue

					# Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
					filename = secure_filename(ufile.filename)
					upload_path = path_without_share + '/' + filename

					# Check the new file name is valid
					try:
						check_name(filename)
					except ValueError:
						ret.append({'name': ufile.filename, 'error': 'Filename not allowed'})
						continue

					file_already_exists = False
					try:
						sfile = conn.getAttributes(share_name, upload_path)
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
							conn.storeFile(share_name, upload_path, ufile, timeout=120)
						else:
							conn.storeFileFromOffset(share_name, upload_path, ufile, offset=byterange_start)

						ret.append({'name': ufile.filename})
					except Exception as ex:
						(title, msg) = self.smb_error_info(ex)
						ret.append({'name': ufile.filename, 'error': title + ": " + msg})
						continue

				return jsonify({'files': ret})

			# POST: RENAME
			elif action == 'rename':
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
				old_path = path_without_share + "/" + old_name
				new_path = path_without_share + "/" + new_name

				# Check existing file/directory exists
				try:
					sfile = conn.getAttributes(share_name, old_path)
				except Exception as ex:
					return self.smb_error_json(ex)

				if sfile.isDirectory:
					typestr = "directory"
				else:
					typestr = "file"

				try:
					conn.rename(share_name, old_path, new_path)
				except Exception as ex:
					return self.smb_error_json(ex)
				else:
					return jsonify({'code': 0, 'msg':
						"The " + typestr + " '" + old_name + "' was renamed to '" + new_name + "' successfully"})

			# POST: COPY
			elif action == 'copy':
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
				src_path  = path_without_share + "/" + src
				dest_path = path_without_share + "/" + dest

				app.logger.debug("asked to copy from " + src + " to " + dest)

				# Check if existing file exists
				try:
					sfile = conn.getAttributes(share_name, src_path)
				except Exception as ex:
					return self.smb_error_json(ex)

				if sfile.isDirectory:
					return jsonify({'code': 1, 'msg': 'Unable to copy a directory!'})

				# Make sure the new file does not exist
				try:
					sfile = conn.getAttributes(share_name, dest_path)
					return jsonify({'code': 1, 'msg': 'The destination filename already exists'})
				except Exception as ex:
					# could not get attributes, so file probably does not exist, so lets continue
					pass

				# read into a local temp file, because you can't 'open' a file handle
				# in pysmb, you have to read the entire thing and store it somewhere
				# oh and we need to reset the file pos 'cos storeFile expects that
				try:
					tfile = tempfile.SpooledTemporaryFile(max_size=1048576)
					conn.retrieveFile(share_name, src_path, tfile)
					tfile.seek(0)
				except Exception as ex:
					return self.smb_error_json(ex)

				try:
					conn.storeFile(share_name, dest_path, tfile, timeout=120)
				except Exception as ex:
					return self.smb_error_json(ex)

				return jsonify({'code': 0, 'msg': 'A copy of "' + src + '" was created as "' + dest + '"'})

			# POST: MAKE DIRECTORY
			elif action == 'mkdir':
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
					conn.createDirectory(share_name, path_without_share + "/" + dirname)
				except Exception as ex:
					return self.smb_error_json(ex)

				return jsonify({'code': 0, 'msg': "The folder '" + dirname + "' was created successfully."})

			# POST: DELETE
			elif action == 'delete':
				try:
					delete_name = request.form['name']
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Invalid parameter'})

				delete_path  = path_without_share + "/" + delete_name

				try:
					sfile = conn.getAttributes(share_name, delete_path)
				except Exception as ex:
					return self.smb_error_json(ex)

				if sfile.isDirectory:
					try:
						conn.deleteDirectory(share_name, delete_path)
					except Exception as ex:
						return self.smb_error_json(ex)

					return jsonify({'code': 0, 'msg': "The directory '" + delete_name + "' was deleted"})

				else:
					try:
						conn.deleteFiles(share_name, delete_path)
					except Exception as ex:
						return self.smb_error_json(ex)

					return jsonify({'code': 0, 'msg': "The file '" + delete_name + "' was deleted"})

			# POST: BOOKMARK
			elif action == 'bookmark':

				if not app.config['REDIS_ENABLED']:
					abort(404)
				if not app.config['BOOKMARKS_ENABLED']:
					abort(404)

				try:
					bookmark_name     = request.form['name']
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Invalid parameter'})

				try:
					# Generate a unique identifier for this bookmark
					bookmark_id = uuid.uuid4().hex

					# Turn this into a redis key for the new bookmark
					redis_key = 'user:' + session['username'] + ':bookmark:' + bookmark_id

					# Store all the details of this bookmark in REDIS
					g.redis.hset(redis_key, 'version', '2')
					g.redis.hset(redis_key, 'function', func_name)
					g.redis.hset(redis_key, 'path', path)
					g.redis.hset(redis_key, 'name', bookmark_name)

					# if we're on a custom server then we need to store the URL
					# to that server otherwise the bookmark is useless.
					if func_name == 'custom':
						if 'custom_uri' in session:
							g.redis.hset(redis_key, 'custom_uri', session['custom_uri'])
						else:
							return jsonify({'code': 1, 'msg': 'Invalid request'})

					# add the new bookmark name to the list of bookmarks for the user
					g.redis.sadd('user:' + session['username'] + ':bookmarks', bookmark_id)

					return jsonify({'code': 0, 'msg': 'Added bookmark ' + bookmark_name,
						'url': url_for('bookmark', bookmark_id=bookmark_id)})

				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Could not save bookmark: ' + str(type(ex)) + " " + str(ex)})

			else:
				return jsonify({'code': 1, 'msg': "An invalid action was specified"})

	def _init_search(self, conn, func_name, share_name, path, path_without_share, query):
		self.conn               = conn
		self.share_name         = share_name
		self.func_name          = func_name
		self.path               = path
		self.path_without_share = path_without_share
		self.query              = query

		self.timeout_reached = False
		self.results         = []

	def _search(self):
		self.timeout_at = int(time.time()) + app.config['SEARCH_TIMEOUT']
		self._rsearch(self.path, self.path_without_share)
		return self.results, self.timeout_reached

	def _rsearch(self, path, path_without_share):
		app.logger.info("rsearch " + path + " , " + path_without_share)
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

			entry = self._sfile_load(sfile, path, self.func_name)

			# Skip hidden files
			if entry['skip']:
				continue

			if self.query.lower() in entry['name'].lower():
				entry['parent_path'] = path
				entry['parent_url'] = url_for(self.func_name, path=path)
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

	def _sfile_load(self, sfile, path, func_name):
		"""Takes a smb SharedFile object and returns a dictionary with information
		about that SharedFile object.
		"""
		entry = {'skip': False,
			'name': sfile.filename,
			'burl': url_for(func_name)}

		if len(path) == 0:
			entry['path'] = entry['name']
		else:
			entry['path'] = path + '/' + entry['name']

		# Skip entries for 'this dir' and 'parent dir'
		if entry['name'] == '.' or entry['name'] == '..':
			entry['skip'] = True

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
