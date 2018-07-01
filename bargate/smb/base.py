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

from time import time

from flask import request, session, render_template, jsonify, abort, make_response
from flask import current_app as app
from PIL import Image
from cStringIO import StringIO

from bargate.lib import fs, errors, userdata, mime, winbind


class LibraryBase(object):
	path = ''

	def smb_action(self, endpoint_name, action, path):
		app.logger.debug("smb_action('" + endpoint_name + "','" + action + "','" + path + "')")

		self.endpoint_name = endpoint_name
		self.action = action
		self.path = path

		if self.endpoint_name == 'custom':
			if not app.config['CONNECT_TO_ENABLED']:
				return errors.stderr('Feature disabled', 'The system administrator has disabled connecting to a custom address')

			self.endpoint_path = unicode(session['custom_uri'])
			self.endpoint_url  = '/custom'
			self.endpoint_title = unicode(session['custom_uri'])
			self.active = 'custom'

		else:
			if not app.sharesConfig.has_section(self.endpoint_name):
				return errors.stderr('Not found', 'The endpoint specified was not found')

			if app.sharesConfig.has_option(self.endpoint_name, 'path'):
				self.endpoint_path = app.sharesConfig.get(self.endpoint_name, 'path')
			else:
				return errors.stderr('Invalid configuration', "'path' is not set on endpoint '" + self.endpoint_name + "'")

			if app.sharesConfig.has_option(self.endpoint_name, 'url'):
				self.endpoint_url = app.sharesConfig.get(self.endpoint_name, 'url')
			else:
				self.endpoint_url = '/' + self.endpoint_name

			self.endpoint_path = self.endpoint_path.replace("%USERNAME%", session['username'])
			self.endpoint_path = self.endpoint_path.replace("%USER%", session['username'])

			if app.config['LDAP_HOMEDIR']:
				if 'ldap_homedir' in session:
					if session['ldap_homedir'] is not None:
						self.endpoint_path = self.endpoint_path.replace("%LDAP_HOMEDIR%", session['ldap_homedir'])

			if app.sharesConfig.has_option(self.endpoint_name, 'display'):
				self.endpoint_title = app.sharesConfig.get(self.endpoint_name, 'display')
			else:
				self.endpoint_title = self.endpoint_name

			if app.sharesConfig.has_option(self.endpoint_name, 'menu'):
				self.active = app.sharesConfig.get(self.endpoint_name, 'menu')
			else:
				self.active = self.endpoint_name

		# Check the path is valid
		try:
			fs.check_path(self.path)
		except ValueError:
			return errors.stderr('Invalid path', 'You tried to navigate to a name of a file or diretory which is invalid')

		# Work out the 'entry name'
		if len(self.path) > 0:
			(a, b, self.entry_name) = self.path.rpartition('/')
		else:
			self.entry_name = u''

		# the address should always start with smb://, we don't support anything else.
		if not self.endpoint_path.startswith("smb://"):
			return errors.stderr('Configuration error', 'The server URL must start with smb://')

		try:
			app.logger.debug("calling library prepare()")
			self.prepare()
			app.logger.debug("calling library connect()")
			self.connect()
		except Exception as ex:
			(title, desc) = self.decode_exception(ex)
			return errors.stderr(title, desc)

		app.logger.debug("smblib.smb_action: Going to call: _action_" + self.action)

		app.logger.info('user: "' + session['username'] + '", endpoint: "' +
			self.endpoint_name + '", endpoint_url: "' + self.endpoint_url + '", action: "' + self.action +
			'", method: ' + str(request.method) + ', path: "' + self.path + '", addr: "' + request.remote_addr +
			'", ua: ' + request.user_agent.string)

		try:
			method = getattr(self, 'action_' + self.action)
		except AttributeError:
			return errors.stderr('Not found', 'The action specified was not found')

		try:
			return method()
		except errors.FatalError as ex:
			return errors.stderr('Error', str(ex))
		except Exception as ex:
			(title, desc) = self.decode_exception(ex)
			return errors.stderr(title, desc)

	def success(self, message):
		return jsonify({'code': 0, 'msg': message})

	def action_browse(self):
		app.logger.debug("action_browse()")

		return render_template('views/browse.html',
			active=self.endpoint_name,
			browse_mode=True,
			epname=self.endpoint_name,
			epurl=self.endpoint_url,
			path=self.path)

	def action_view(self):
		app.logger.debug("action_view()")

		return self.action_download(view=True)

	def action_bookmark(self):
		app.logger.debug("action_bookmark()")

		if not app.config['REDIS_ENABLED']:
			raise errors.FatalError('Persistent storage (redis) is disabled')
		if not app.config['BOOKMARKS_ENABLED']:
			raise errors.FatalError('Bookmarks are disabled')

		try:
			bookmark_name = request.form['name']
		except Exception:
			raise errors.FatalError("Missing parameter")

		if self.endpoint_name == 'custom':
			if 'custom_uri' not in session:
				raise errors.FatalError("Missing parameter")

		try:
			bmark = userdata.save_bookmark(bookmark_name, self.endpoint_name, self.path)
		except Exception as ex:
			raise errors.FatalError('Could not set bookmark, ' + type(ex).__name__ + ": " + str(ex))

		return jsonify({'code': 0, 'bmark': bmark})

	def action_search(self):
		app.logger.debug("action_seach()")

		if not app.config['SEARCH_ENABLED']:
			raise errors.FatalError("Search is not enabled")

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

		self.query = request.args.get('q')
		self.timeout_reached = False
		self.results         = []
		self.timeout_at = int(time()) + app.config['SEARCH_TIMEOUT']
		self.rsearch()

		return jsonify({'code': 0,
			'results': self.results,
			'query': self.query,
			'crumbs': crumbs,
			'root_name': self.endpoint_title,
			'epname': self.endpoint_name,
			'epurl': self.endpoint_url,
			'path': self.path,
			'timeout_reached': self.timeout_reached,
			'parent': parent,
			'parent_path': parent_path})

	def action_ls(self):
		app.logger.debug("action_ls()")

		(files, dirs, shares) = self.ls()

		no_items = False
		if not files and not dirs and not shares:
			no_items = True
			files = None
			dirs = None
			shares = None
		else:
			if not files:
				files = None
			if not dirs:
				dirs = None
			if not shares:
				shares = None

		# only allow bookmarking if we're not at the endpoint root
		bmark_enabled = False
		if len(self.path) > 0:
			bmark_enabled = True

		# Build a breadcrumb trail
		parts = self.path.split('/')
		b4    = ''
		crumbs = []
		for crumb in parts:
			if len(crumb) > 0:
				crumbs.append({'name': crumb, 'path': b4 + crumb})
				b4 = b4 + crumb + '/'

		parent = False
		parent_path = None
		if len(crumbs) > 1:
			parent     = True
			parent_path = crumbs[-2]['path']
		elif len(crumbs) == 1:
			parent = True
			parent_path = ''

		if self.path is None:
			self.path = ''

		return jsonify({'code': 0,
			'dirs': dirs,
			'files': files,
			'shares': shares,
			'crumbs': crumbs,
			'bmark_path': self.path + ' in ' + self.endpoint_title,
			'bmark': bmark_enabled,
			'root_name': self.endpoint_title,
			'epname': self.endpoint_name,
			'epurl': self.endpoint_url,
			'path': self.path,
			'no_items': no_items,
			'parent': parent,
			'parent_path': parent_path})

	def action_stat(self):
		app.logger.debug("action_stat()")

		finfo = self.stat()

		if not finfo.type == fs.TYPE_FILE:
			raise errors.FatalError("You cannot stat a directory")

		(ftype, mtype) = mime.filename_to_mimetype(self.entry_name)

		data = {
			'code': 0,
			'filename': self.entry_name,
			'size': finfo.size,
			'atime': finfo.atime,
			'mtime': finfo.mtime,
			'ftype': ftype,
			'mtype': mtype,
			'owner': "N/A",
			'group': "N/A",
		}

		try:
			(owner, group) = self.get_owner_group()

			if app.config['WBINFO_LOOKUP']:
				data['owner'] = winbind.sid_to_name(owner)
				data['group'] = winbind.sid_to_name(group)
		except Exception:
			pass

		return jsonify(data)

	def action_preview(self):
		app.logger.debug("action_image_preview()")

		if not app.config['IMAGE_PREVIEW']:
			abort(400)

		try:
			finfo = self.stat()
		except Exception:
			abort(400)

		if not finfo.type == fs.TYPE_FILE:
			abort(400)

		(ftype, mtype) = mime.filename_to_mimetype(self.entry_name)

		if finfo.size > app.config['IMAGE_PREVIEW_MAX_SIZE']:
			abort(403)

		if mtype not in mime.pillow_supported:
			abort(400)

		try:
			fp = self.get_spooled_fp()
			img = Image.open(fp).convert('RGB')
			img.thumbnail((app.config['IMAGE_PREVIEW_WIDTH'], app.config['IMAGE_PREVIEW_HEIGHT']))

			thumbnail = StringIO()
			img.save(thumbnail, 'JPEG', quality=app.config['IMAGE_PREVIEW_QUALITY'])
			thumbnail.seek(0)

			return fs.send_fp(thumbnail, finfo.mtime, 'image/jpeg')
		except Exception as ex:
			app.logger.error("Could not generate image thumbnail: " + type(ex).__name__ + ": " + str(ex))
			abort(400)

	def action_download(self, view=False):
		app.logger.debug("action_download()")

		finfo = self.stat()
		if finfo.type == fs.TYPE_DIR:
			raise errors.FatalError("You tried to download a directory")

		(ftype, mtype) = mime.filename_to_mimetype(self.entry_name)

		attach = True
		if view:
			if mime.view_in_browser(mtype):
				attach = False

		fp = self.get_fp()

		if attach:
			resp = make_response(fs.send_attachment(fp, self.entry_name, finfo.mtime, mtype))
		else:
			resp = make_response(fs.send_fp(fp, finfo.mtime, mtype))

		resp.headers['Content-length'] = finfo.size
		return resp

	def action_upload(self):
		app.logger.debug("action_upload()")

		ret = []

		uploaded_files = request.files.getlist("files[]")

		for fp in uploaded_files:

			if fs.banned_filename(fp.filename):
				ret.append({'name': fp.filename, 'error': 'File type not allowed'})
				continue

			# Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
			filename = fs.secure_filename(fp.filename)

			# Check the new file name is valid
			try:
				fs.check_name(filename)
			except ValueError:
				ret.append({'name': fp.filename, 'error': 'Filename not allowed'})
				continue

			try:
				finfo = self.stat(filename)
				file_already_exists = True
			except errors.NotFoundError:
				file_already_exists = False
			except Exception as ex:
				(title, msg) = self.decode_exception(ex)
				ret.append({'name': fp.filename,
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
					if not userdata.get_overwrite_on_upload():
						ret.append({'name': fp.filename,
							'error': 'File already exists. You can enable overwriting files in Settings.'})
						continue

					# Now ensure we're not trying to upload a file on top of a directory (can't do that!)
					if finfo.type == fs.TYPE_DIR:
						ret.append({'name': fp.filename,
							'error': "That name already exists and is a directory"})
						continue

			try:
				self.upload(filename, fp, byterange_start)
				ret.append({'name': fp.filename})
			except Exception as ex:
				(title, msg) = self.decode_exception(ex)
				ret.append({'name': fp.filename, 'error': title + ": " + msg})
				continue

		return jsonify({'files': ret})

	def action_rename(self):
		app.logger.debug("action_rename()")

		try:
			old_name = request.form['old_name']
			new_name = request.form['new_name']
		except KeyError:
			raise errors.FatalError("Missing parameter")

		try:
			fs.check_name(new_name)
		except ValueError:
			raise errors.FatalError("Invalid name")

		finfo = self.stat(old_name)

		if finfo.type == fs.TYPE_FILE:
			typestr = "file"
		elif finfo.type == fs.TYPE_DIR:
			typestr = "directory"
		else:
			raise errors.FatalError("You can only rename files or directories")

		self.rename(old_name, new_name)
		return self.success("The " + typestr + " '" + old_name + "' was renamed to '" + new_name + "' successfully")

	def action_copy(self):
		app.logger.debug("action_copy()")

		try:
			src  = request.form['src']
			dest = request.form['dest']
		except KeyError:
			raise errors.FatalError("Missing parameter")

		try:
			fs.check_name(dest)
		except ValueError:
			raise errors.FatalError("Invalid name")

		# Ensure the src file exists and is not a directory
		src_finfo = self.stat(src)

		if src_finfo.type != fs.TYPE_FILE:
			raise errors.FatalError("The source item must be a file")

		# Make sure the dest file does not exist
		try:
			self.stat(dest)
		except errors.NotFoundError:
			raise errors.FatalError("The destination filename already exists")

		self.copy(src, dest, src_finfo.size)
		return self.success('A copy of "' + src + '" was created as "' + dest + '"')

	def action_mkdir(self):
		app.logger.debug("action_mkdir()")

		try:
			name = request.form['name']
		except KeyError:
			raise errors.FatalError("Missing parameter")

		try:
			fs.check_name(name)
		except ValueError:
			raise errors.FatalError("Invalid directory name")

		self.mkdir(name)
		return self.success("The directory '" + name + "' was created successfully.")

	def action_delete(self):
		app.logger.debug("action_delete()")

		try:
			name = request.form['name']
		except KeyError:
			raise errors.FatalError("Missing parameter")

		finfo = self.stat(name)

		if finfo.type == fs.TYPE_DIR:
			self.delete_dir(name)
			return self.success("The directory '" + name + "' was deleted")

		elif finfo.type == fs.TYPE_FILE:
			self.delete_file(name)
			return self.success("The file '" + name + "' was deleted")

		else:
			return errors.FatalError("You tried to delete something other than a file or directory")

	def rsearch(self, path_suffix=None):
		app.logger.warn("rsearch called: " + unicode(path_suffix))

		try:
			(files, dirs, shares) = self.ls(path_suffix, strip_data=False)
		except Exception as ex:
			app.logger.warn("Search encountered an exception, " + type(ex).__name__ + ": " + unicode(ex))
			return

		entries = files + dirs
		for entry in entries:
			if int(time()) >= self.timeout_at:
				self.timeout_reached = True
				break

			if self.query.lower() in entry['name'].lower():
				entry['parent_path'] = self.path
				if path_suffix is not None:
					if len(self.path) > 0:
						entry['parent_path'] = self.path + '/' + path_suffix
				self.results.append(entry)

			# Search subdirectories if we found one
			if entry['type'] == fs.TYPE_DIR:
				if path_suffix is not None:
					self.rsearch(path_suffix + '/' + entry['name'])
				else:
					self.rsearch(entry['name'])
