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

import os         # used in file modes when writing to files
import io         # used for 'default buffer size'
import stat       # used for checking file type via unix mode
import urllib     # used in SMBClientWrapper for URL-quoting strings
import time       # used in search (timeout)
import StringIO   # used in image previews

import smbc
from flask import send_file, request, session
from flask import abort, flash, make_response, jsonify
from PIL import Image

from bargate import app
from bargate.smb.base import LibraryBase
from bargate.lib import fs, misc, user, userdata, mime, winbind


class FileStat:
	"""A wrapper class to stat data returned from pysmbc. This class just makes
	it easier to access the data and also provides a 'type' attribute that the
	normal stat doesn't bother with"""

	def __init__(self, fstat):
		self.mode  = fstat[0]  # permissions mode
		self.ino   = fstat[1]  # inode number
		self.dev   = fstat[2]  # device number
		self.nlink = fstat[3]  # number of links
		self.uid   = fstat[4]  # user ID
		self.gid   = fstat[5]  # group ID
		self.size  = fstat[6]  # size in bytes
		self.atime = fstat[7]  # access time
		self.mtime = fstat[8]  # modify time
		self.ctime = fstat[9]  # change time

		if stat.S_ISDIR(self.mode):
			self.type = fs.EntryType.dir
		elif stat.S_ISREG(self.mode):
			self.type = fs.EntryType.file
		else:
			self.type = fs.EntryType.other


class SMBClientWrapper:
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
		return FileStat(self.smbclient.stat(url))

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


class BargateSMBLibrary(LibraryBase):
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
			flash('Unexpected SMB authentication error: ' + str(ex), 'alert-danger')
			return False

		app.logger.debug("bargate.lib.user.auth auth smb success")

	def smb_action(self, endpoint_name, action, path):
		app.logger.debug("smb_action('" + endpoint_name + "','" + action + "','" + path + "')")

		self.smb_connection_init(endpoint_name, action, path)

		if not self.endpoint_path.endswith('/'):
			self.endpoint_path = self.endpoint_path + '/'

		# All requests to the SMB library need to include the addr (defined in shares.conf)
		# and the path the user has navigated to, combined.
		self.addr = self.endpoint_path + self.path
		if self.addr.endswith('/'):
			self.addr = self.addr[:-1]

		# Prepare to talk to the file server
		self.libsmbclient = SMBClientWrapper()

		app.logger.info('user: "' + session['username'] + '", addr: "' + self.addr + '", endpoint: "' +
			self.endpoint_name + '", endpoint_url: "' + self.endpoint_url + '", action: "' + self.action +
			'", method: ' + str(request.method) + ', path: "' + self.path + '", addr: "' + request.remote_addr +
			'", ua: ' + request.user_agent.string)

		return self.action_dispatch()

	def _action_download(self, view=False):
		app.logger.debug("_action_download()")

		try:
			fstat = self.libsmbclient.stat(self.full_addr)
		except Exception as ex:
			return self.smb_error(ex)

		if not fstat.type == fs.EntryType.file:
			abort(400)

		try:
			file_object = self.libsmbclient.open(self.full_addr)

			# Default to sending files as an 'attachment' ("Content-Disposition: attachment")
			attach = True

			# guess a mimetype
			(ftype, mtype) = mime.filename_to_mimetype(self.entry_name)

			# If the user requested to 'view' (don't download as an attachment)
			# make sure we allow it for that filetype
			if view:
				if mime.view_in_browser(mtype):
					attach = False

			# Send the file to the user
			resp = make_response(send_file(file_object,
				add_etags=False,
				as_attachment=attach,
				attachment_filename=self.entry_name,
				mimetype=mtype))
			resp.headers['content-length'] = str(fstat.size)
			app.logger.debug("returning response")
			return resp

		except Exception as ex:
			return self.smb_error(ex)

	def _action_preview(self):
		app.logger.debug("_action_image_preview()")

		if not app.config['IMAGE_PREVIEW']:
			abort(400)

		try:
			fstat = self.libsmbclient.stat(self.full_addr)
		except Exception:
			abort(400)

		# ensure item is a file
		if not fstat.type == fs.EntryType.file:
			abort(400)

		# guess a mimetype
		(ftype, mtype) = mime.filename_to_mimetype(self.entry_name)

		# Check size is not too large for a preview
		if fstat.size > app.config['IMAGE_PREVIEW_MAX_SIZE']:
			abort(403)

		# Only preview files that Pillow supports
		if mtype not in mime.pillow_supported:
			abort(400)

		# Open the file
		try:
			file_object = self.libsmbclient.open(self.full_addr)
		except Exception:
			abort(400)

		# Read the file into memory first (hence a file size limit) because PIL/Pillow tries readline()
		# on pysmbc's File like objects which it doesn't support
		try:
			sfile = StringIO.StringIO(file_object.read())
			pil_img = Image.open(sfile).convert('RGB')
			pil_img.thumbnail((app.config['IMAGE_PREVIEW_WIDTH'], app.config['IMAGE_PREVIEW_HEIGHT']))

			ifile = StringIO.StringIO()
			pil_img.save(ifile, 'PNG', compress_level=app.config['IMAGE_PREVIEW_LEVEL'])
			ifile.seek(0)

			return send_file(ifile, mimetype='image/jpeg', add_etags=False)
		except Exception:
			abort(400)

	def _action_stat(self):
		app.logger.debug("_action_stat()")

		try:
			fstat = self.libsmbclient.stat(self.full_addr)
		except Exception as ex:
			return self.return_exception(ex)

		# ensure item is a file
		if not fstat.type == fs.EntryType.file:
			return jsonify({'code': 1, 'msg': 'You cannot stat a directory!'})

		# guess mimetype
		(ftype, mtype) = mime.filename_to_mimetype(self.entry_name)

		data = {
			'code': 0,
			'filename': self.entry_name,
			'size': fstat.size,
			'atime': misc.ut_to_string(fstat.atime),
			'mtime': misc.ut_to_string(fstat.mtime),
			'ftype': ftype,
			'mtype': mtype,
			'owner': "N/A",
			'group': "N/A",
		}

		try:
			data['owner'] = self.libsmbclient.getxattr(self.full_addr, smbc.XATTR_OWNER)
			data['group'] = self.libsmbclient.getxattr(self.full_addr, smbc.XATTR_GROUP)

			if app.config['WBINFO_LOOKUP']:
				data['owner'] = winbind.sid_to_name(data['owner'])
				data['group'] = winbind.sid_to_name(data['group'])
		except Exception as ex:
			pass

		return jsonify(data)

	def _action_search(self):
		app.logger.debug("_action_seach()")

		if not app.config['SEARCH_ENABLED']:
			abort(404)

		# Build a breadcrumbs trail #
		crumbs = []
		parts = self.path.split('/')
		b4 = ''

		# Build up a list of dicts, each dict representing a crumb
		for crumb in parts:
			if len(crumb) > 0:
				crumbs.append({'name': crumb, 'path': b4 + crumb})
				b4 = b4 + crumb + '/'

		parent      = False
		parent_path = None
		if len(crumbs) > 1:
			parent      = True
			parent_path = crumbs[-2]['path']
		elif len(crumbs) == 1:
			parent      = True
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

	def _action_ls(self):
		app.logger.debug("_action_ls()")

		try:
			directory_entries = self.libsmbclient.ls(self.full_addr)
		except smbc.NotDirectoryError as ex:
			return jsonify({'code': 1, 'msg': 'The given path is not a directory'})
		except Exception as ex:
			return self.return_exception(ex)

		try:
			dirs   = []
			files  = []
			shares = []

			for dentry in directory_entries:
				entry = self._direntry_load(dentry)

				if not entry['skip']:
					etype = entry['type']
					entry.pop('skip', None)
					entry.pop('type', None)

					if etype == fs.EntryType.file:
						files.append(entry)
					elif etype == fs.EntryType.dir:
						dirs.append(entry)
					elif etype == fs.EntryType.share:
						shares.append(entry)

			bmark_enabled   = False
			buttons_enabled = False
			no_items        = False
			crumbs          = []
			parent          = False
			parent_path     = None

			if len(shares) == 0:
				# are there any items?
				if len(files) == 0 and len(dirs) == 0:
					no_items = True

				# only allow bookmarking if we're not at the root
				if len(self.path) > 0:
					bmark_enabled = True

				buttons_enabled = True

				# Build a breadcrumbs trail #
				parts = self.path.split('/')
				b4    = ''

				# Build up a list of dicts, each dict representing a crumb
				for crumb in parts:
					if len(crumb) > 0:
						crumbs.append({'name': crumb, 'path': b4 + crumb})
						b4 = b4 + crumb + '/'

				if len(crumbs) > 1:
					parent     = True
					parent_path = crumbs[-2]['path']
				elif len(crumbs) == 1:
					parent = True
					parent_path = ''

			return jsonify({'code': 0,
				'dirs': dirs,
				'files': files,
				'shares': shares,
				'crumbs': crumbs,
				'buttons': buttons_enabled,
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
			return self.return_exception(ex)

	def _action_upload(self):
		app.logger.debug("_action_upload()")

		ret = []

		uploaded_files = request.files.getlist("files[]")

		for ufile in uploaded_files:

			if fs.banned_filename(ufile.filename):
				ret.append({'name': ufile.filename, 'error': 'File type not allowed'})
				continue

			# Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
			filename = fs.secure_filename(ufile.filename)
			upload_uri = self.full_addr + '/' + filename

			# Check the new file name is valid
			try:
				fs.check_name(filename)
			except ValueError:
				ret.append({'name': ufile.filename, 'error': 'Filename not allowed'})
				continue

			# Check to see if the file exists
			fstat = None
			try:
				fstat = self.libsmbclient.stat(upload_uri)
			except smbc.NoEntryError:
				app.logger.debug("Upload filename of " + upload_uri + " does not exist, ignoring")
				# It doesn't exist so lets continue to upload
			except Exception as ex:
				ret.append({'name': ufile.filename, 'error': 'Failed to stat existing file: ' + str(ex)})
				continue

			byterange_start = 0
			if 'Content-Range' in request.headers:
				byterange_start = int(request.headers['Content-Range'].split(' ')[1].split('-')[0])
				app.logger.debug("Chunked file upload request: Content-Range sent with byte range start of " +
					str(byterange_start) + " with filename " + filename)

			try:
				# Check if we're writing from the start of the file
				if byterange_start == 0:
					# We're truncating an existing file, or creating a new file
					# If the file already exists, check to see if we should overwrite
					if fstat is not None:
						if not userdata.get_overwrite_on_upload():
							ret.append({'name': ufile.filename,
								'error': 'File already exists. You can enable overwriting files in Settings.'})
							continue

						# Now ensure we're not trying to upload a file on top of a directory (can't do that!)
						fstat = self.libsmbclient.stat(upload_uri)
						if fstat.type == fs.EntryType.dir:
							ret.append({'name': ufile.filename, 'error':
								"That name already exists and is a directory"})
							continue

					# Open the file for the first time, truncating or creating it if necessary
					app.logger.debug("Opening for writing with O_CREAT and TRUNC")
					wfile = self.libsmbclient.open(upload_uri, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
				else:
					# Open the file and seek to where we are going to write the additional data
					app.logger.debug("Opening for writing with O_WRONLY")
					wfile = self.libsmbclient.open(upload_uri, os.O_WRONLY)
					wfile.seek(byterange_start)

				while True:
					buff = ufile.read(io.DEFAULT_BUFFER_SIZE)
					if not buff:
						break
					wfile.write(buff)

				wfile.close()
				ret.append({'name': ufile.filename})

			except Exception as ex:
				ret.append({'name': ufile.filename, 'error': 'Could not upload file: ' + str(ex)})
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
			fs.check_name(new_name)
		except ValueError:
			return jsonify({'code': 1, 'msg': 'The new name is invalid'})

		# Build paths
		old_path = self.full_addr + "/" + old_name
		new_path = self.full_addr + "/" + new_name

		# get the item type of the existing 'filename'
		fstat = self.libsmbclient.stat(old_path)

		if fstat.type == fs.EntryType.file:
			typestr = "file"
		elif fstat.type == fs.EntryType.dir:
			typestr = "directory"
		else:
			return jsonify({'code': 1, 'msg': 'You can only rename files or folders!'})

		try:
			self.libsmbclient.rename(old_path, new_path)
		except Exception as ex:
			return self.return_exception(ex)

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
			fs.check_name(dest)
		except ValueError:
			return jsonify({'code': 1, 'msg': 'The new name is invalid'})

		# Build paths
		src_path  = self.full_addr + "/" + src
		dest_path = self.full_addr + "/" + dest

		try:
			source_stat = self.libsmbclient.stat(src_path)
		except Exception as ex:
			return self.return_exception(ex)

		if not source_stat.type == fs.EntryType.file:
			return jsonify({'code': 1, 'msg': 'Unable to copy a directory!'})

		# Make sure the dest file doesn't exist
		try:
			self.libsmbclient.stat(dest_path)
			return jsonify({'code': 1, 'msg': 'The destination filename already exists'})
		except smbc.NoEntryError as ex:
			pass
		except Exception as ex:
			return self.return_exception(ex)

		# Open the source so we can read from it
		try:
			source_fh = self.libsmbclient.open(src_path)
		except Exception as ex:
			return self.return_exception(ex)

		# Open the destination file to write to
		try:
			dest_fh = self.libsmbclient.open(dest_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
		except Exception as ex:
			return self.return_exception(ex)

		# copy the data in 1024 byte chunks
		try:
			location = 0
			while(location >= 0 and location < source_stat.size):
				chunk = source_fh.read(1024)
				dest_fh.write(chunk)
				location = source_fh.seek(1024, location)

		except Exception as ex:
			return self.return_exception(ex)

		return jsonify({'code': 0, 'msg': 'A copy of "' + src + '" was created as "' + dest + '"'})

	def _action_mkdir(self):
		app.logger.debug("_action_mkdir()")

		try:
			dirname = request.form['name']
		except Exception as ex:
			return jsonify({'code': 1, 'msg': 'Invalid parameter'})

		# check the proposed new name is valid
		try:
			fs.check_name(dirname)
		except ValueError:
			return jsonify({'code': 1, 'msg': 'That directory name is invalid'})

		try:
			self.libsmbclient.mkdir(self.full_addr + '/' + dirname)
		except Exception as ex:
			return self.return_exception(ex)

		return jsonify({'code': 0, 'msg': "The folder '" + dirname + "' was created successfully."})

	def _action_delete(self):
		app.logger.debug("_action_delete()")

		try:
			delete_name = request.form['name']
		except Exception as ex:
			return jsonify({'code': 1, 'msg': 'Invalid parameter'})

		delete_path  = self.full_addr + "/" + delete_name

		fstat = self.libsmbclient.stat(delete_path)

		if fstat.type == fs.EntryType.file:
			try:
				self.libsmbclient.delete(delete_path)
			except Exception as ex:
				return self.return_exception(ex)
			else:
				return jsonify({'code': 0, 'msg': "The file '" + delete_name + "' was deleted"})

		elif fstat.type == fs.EntryType.dir:

			# Against some SMB servers (Samba!) no error is generated by pysmbc when trying to delete a
			# directory which is not empty (!). Thus, sadly, we must check to see if the directory is empty
			# first and then raise an error if it is not.
			try:
				contents = self.libsmbclient.ls(delete_path)
			except Exception as ex:
				return self.return_exception(ex)

			# the directory contents always returns '.' and '..'
			contents = filter(lambda s: not (s.name == '.' or s.name == '..'), contents)
			if len(contents) > 0:
				return jsonify({'code': 1, 'msg': "The directory '" + delete_name + "' is not empty"})

			try:
				self.libsmbclient.rmdir(delete_path)
			except Exception as ex:
				return self.return_exception(ex)
			else:
				return jsonify({'code': 0, 'msg': "The directory '" + delete_name + "' was deleted"})
		else:
			return jsonify({'code': 1, 'msg': 'You tried to delete something other than a file or directory'})

	def _action_bookmark(self):
		app.logger.debug("_action_bookmark()")
		self.set_bookmark()

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

			entry = self._direntry_load(dentry, path)

			# Skip hidden files
			if entry['skip']:
				continue

			# Check if the filename matched
			if self.query.lower() in entry['name'].lower():
				app.logger.debug("_rsearch: Matched: " + entry['name'])
				entry['parent_path'] = path
				self.results.append(entry)

			# Search subdirectories if we found one
			if entry['type'] == fs.EntryType.dir:
				if len(path) > 0:
					sub_path = path + "/" + entry['name']
				else:
					sub_path = entry['name']

				self._rsearch(sub_path)

	def _direntry_load(self, dentry, path=None):
		entry = {'skip': False, 'name': dentry.name, 'epurl': self.endpoint_url}

		if path is None:
			path = self.path

		# old versions of pysmbc return 'str' objects rather than unicode
		if isinstance(entry['name'], str):
			entry['name'] = entry['name'].decode("utf-8")

		if len(self.path) == 0:
			entry['path'] = entry['name']
		else:
			entry['path'] = path + '/' + entry['name']

		# Skip entries for 'this dir' and 'parent dir'
		if entry['name'] == '.' or entry['name'] == '..':
			entry['skip'] = True
			return entry

		# hide files which we consider 'hidden'
		if not userdata.get_show_hidden_files():
			if entry['name'].startswith('.'):
				entry['skip'] = True
			if entry['name'].startswith('~$'):
				entry['skip'] = True
			if entry['name'] in ['desktop.ini', '$RECYCLE.BIN', 'RECYCLER', 'Thumbs.db']:
				entry['skip'] = True

		if dentry.smbc_type in [fs.EntryType.file, fs.EntryType.dir, fs.EntryType.share]:
			entry['type'] = dentry.smbc_type

			if dentry.smbc_type == fs.EntryType.share:
				if entry['name'].endswith == "$":
					entry['skip'] = True

		else:
			entry['type'] = fs.EntryType.other
			entry['skip'] = True

		if not entry['skip']:
			if entry['type'] == fs.EntryType.file:
				# Generate 'mtype', 'mtyper' and 'icon'
				entry['icon'] = 'file-text-o'
				(entry['mtype'], entry['mtyper']) = mime.filename_to_mimetype(entry['name'])
				entry['icon'] = mime.mimetype_to_icon(entry['mtyper'])

				try:
					fstat = self.libsmbclient.stat(self.full_addr + '/' + entry['name'])
				except Exception as ex:
					app.logger.debug("stat failed against " + self.full_addr + '/' + entry['name'])
					app.logger.debug(str(ex))
					# If the file stat failed we return a result with the data missing
					# rather than fail the entire page load
					entry['mtimer'] = 0
					entry['mtime']  = "Unknown"
					entry['size']   = 0
					entry['error']  = True
					return entry

				entry['mtimer'] = fstat.mtime
				entry['atime']  = misc.ut_to_string(fstat.atime)
				entry['mtime']  = misc.ut_to_string(fstat.mtime)
				entry['size']   = fstat.size

				# Image previews
				if app.config['IMAGE_PREVIEW'] and entry['mtyper'] in mime.pillow_supported:
					if fstat.size <= app.config['IMAGE_PREVIEW_MAX_SIZE']:
						entry['img'] = True

				# View-in-browser download type
				if mime.view_in_browser(entry['mtyper']):
					entry['view'] = True

		return entry

	def decode_exception(self, ex):
		if isinstance(ex, smbc.PermissionError):
			return ("Permission Denied",
				"You do not have permission to perform the action")

		elif isinstance(ex, smbc.NoEntryError):
			return ("No such file or directory",
				"The file or directory was not found")

		elif isinstance(ex, smbc.NoSpaceError):
			return ("No space left on device",
				"There is no space left on the server. You may have exceeded your usage allowance")

		elif isinstance(ex, smbc.ExistsError):
			if self.action == 'ls':
				return ("Not found",
					"The directory specified does not exist")
			else:
				return ("File or directory already exists",
					"The file or directory you attempted to create already exists")

		elif isinstance(ex, smbc.NotEmptyError):
			return ("The directory is not empty",
				"The directory is not empty so cannot be deleted")

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
