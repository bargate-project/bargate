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

from bargate import app
import string, os, io, smbc, sys, stat, pprint, urllib, re, time, glob
import StringIO, traceback
from flask import send_file, request, session, g, redirect, url_for
from flask import abort, flash, make_response, jsonify, render_template
from bargate.lib.core import banned_file, secure_filename, check_path
from bargate.lib.core import ut_to_string, wb_sid_to_name, check_name
import bargate.lib.errors
from bargate.lib.errors import stderr
import bargate.lib.userdata
import bargate.lib.mime

# pysmbc entry types
SMB_ERR         = -1
SMB_OTHER       = 0
SMB_WORKGROUP   = 1
SMB_SERVER      = 2
SMB_SHARE       = 3
SMB_PRINTER     = 4
SMB_COMMS_SHARE = 5
SMB_IPC         = 6
SMB_DIR         = 7
SMB_FILE        = 8
SMB_LINK        = 9

### Python imaging stuff
from PIL import Image

class FileStat:
	def __init(self,fstat):
		self.mode  = fstat[0] # permissions mode
		self.ino   = fstat[1] # inode number
		self.dev   = fstat[2] # device number
		self.nlink = fstat[3] # number of links
		self.uid   = fstat[4] # user ID
		self.gid   = fstat[5] # group ID
		self.size  = fstat[6] # size in bytes
		self.atime = fstat[7] # access time
		self.mtime = fstat[8] # modify time
		self.ctime = fstat[9] # change time

		if stat.S_ISDIR(self.mode):
			self.type = SMB_DIR
		elif stat.S_ISREG(self.mode):
			self.type = SMB_FILE
		else:
			self.type = SMB_OTHER

class SMBClientWrapper:
	"""the pysmbc library expects URL quoted str objects (as in, Python 2.x
	strings, rather than unicode strings. This wrapper class takes unicode
	non-quoted arguments and then silently converts the inputs into urllib 
	quoted str objects instead, making use of the library a lot easier"""

	def __init__(self):
		self.smbclient = smbc.Context(auth_fn=bargate.lib.user.get_smbc_auth)

	def _convert(self,url):
		# input will be of the form smb://location.location/path/path/path
		# we need to only URL quote the path, we must not quote the rest

		if not url.startswith("smb://"):
			raise Exception("URL must start with smb://")

		url = url.replace("smb://","")
		(server,sep,path) = url.partition('/')

		if isinstance(url, str):
			return "smb://" + server.encode('utf-8') + "/" + urllib.quote(path)
		elif isinstance(url, unicode):
			return "smb://" + server + "/" + urllib.quote(path.encode('utf-8'))
		else:
			# uh.. hope for the best?
			return var

	def stat(self,url):
		if url.endswith('/'):
			url = url[:-1]

		url = self._convert(url)
		return FileStat(self.smbclient.stat(url))

	def open(self,url,mode=None):
		url = self._convert(url)

		if mode is None:
			return self.smbclient.open(url)
		else:
			return self.smbclient.open(url,mode)

	def ls(self,url):
		url = self._convert(url)
		return self.smbclient.opendir(url).getdents()

	def rename(self,old,new):
		old = self._convert(old)
		new = self._convert(new)
		return self.smbclient.rename(old,new)

	def mkdir(self,url,mode=0755):
		url = self._convert(url)
		return self.smbclient.mkdir(url,mode)

	def rmdir(self,url):
		url = self._convert(url)
		return self.smblcient.rmdir(url)

	def delete(self,url):
		url = self._convert(url)
		return self.smbclient.unlink(url)

	def getxattr(self,url,attr):
		url = self._convert(url)
		return self.smbclient.getxattr(url,attr)

################################################################################
################################################################################

class backend_pysmbc:

################################################################################

	def smb_action(self,srv_path,func_name,active=None,display_name="Home",action='browse',path=''):

		app.logger.debug("path was " + path + " on " + request.url)

		## default the 'active' variable to the function name
		if active == None:
			active = func_name

		## If the method is POST then 'action' is sent via a POST parameter 
		## rather than via a so-called "GET" parameter in the URL
		if request.method == 'POST':
			action = request.form['action']

		## ensure srv_path (the server URI and share) ends with a trailing slash
		if not srv_path.endswith('/'):
			srv_path = srv_path + '/'

		## srv_path should always start with smb://, we don't support anything else.
		if not srv_path.startswith("smb://"):
			return stderr("Invalid server path","The server URL must start with smb://")

		## Check the path is valid
		try:
			check_path(path)
		except ValueError as e:
			return bargate.lib.errors.invalid_path()

		## Build the URI
		uri = srv_path + path
		if uri.endswith('/'):
			uri = uri[:-1]

		## Work out the 'entry name'
		if len(path) > 0:
			(a,b,entry_name) = path.rpartition('/')
		else:
			entry_name = u""

		## Prepare to talk to the file server
		libsmbclient = SMBClientWrapper()

		app.logger.info('user: "' + session['username'] + '", srv_path: "' + srv_path + '", endpoint: "' + func_name + '", action: "' + action + '", method: ' + str(request.method) + ', path: "' + path + '", addr: "' + request.remote_addr + '", ua: ' + request.user_agent.string)


		############################################################################
		## HTTP GET ACTIONS ########################################################
		# actions: download/view, browse, stat
		############################################################################

		if request.method == 'GET':

	################################################################################
	# DOWNLOAD OR 'VIEW' FILE
	################################################################################

			if action == 'download' or action == 'view':

				try:
					fstat = libsmbclient.stat(uri)
				except Exception as ex:
					return self.smb_error(ex)

				if not fstat.type == SMB_FILE:
					abort(400)

				try:
					file_object = libsmbclient.open(uri)

					## Default to sending files as an 'attachment' ("Content-Disposition: attachment")
					attach = True

					## guess a mimetype
					(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entry_name)

					## If the user requested to 'view' (don't download as an attachment) make sure we allow it for that filetype
					if action == 'view':
						if bargate.lib.mime.view_in_browser(mtype):
							attach = False

					## Send the file to the user
					resp = make_response(send_file(file_object,add_etags=False,as_attachment=attach,attachment_filename=entry_name,mimetype=mtype))
					resp.headers['content-length'] = str(fstat.size)
					return resp
	
				except Exception as ex:
					return self.smb_error(ex)

			####################
			# GET: IMAGE PREVIEW
			####################
			elif action == 'preview':
				if not app.config['IMAGE_PREVIEW']:
					abort(400)

				try:
					fstat = libsmbclient.stat(uri)
				except Exception as ex:
					abort(400)

				## ensure item is a file
				if not fstat.type == SMB_FILE:
					abort(400)
				
				## guess a mimetype
				(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entry_name)

				## Check size is not too large for a preview
				if fstat.size > app.config['IMAGE_PREVIEW_MAX_SIZE']:
					abort(403)

				## Only preview files that Pillow supports
				if not mtype in bargate.lib.mime.pillow_supported:
					abort(400)

				## Open the file
				try:
					file_object = libsmbclient.open(uri)
				except Exception as ex:
					abort(400)
			
				## Read the file into memory first (hence a file size limit) because PIL/Pillow tries readline()
				## on pysmbc's File like objects which it doesn't support
				try:
					sfile = StringIO.StringIO(file_object.read())
					pil_img = Image.open(sfile).convert('RGB')
					size = 200, 200
					pil_img.thumbnail(size, Image.ANTIALIAS)

					img_io = StringIO.StringIO()
					pil_img.save(img_io, 'JPEG', quality=85)
					img_io.seek(0)
					return send_file(img_io, mimetype='image/jpeg',add_etags=False)
				except Exception as ex:
					abort(400)

	################################################################################
	# STAT FILE/DIR - json ajax request
	################################################################################
			
			elif action == 'stat':

				try:
					fstat = libsmbclient.stat(uri)
				except Exception as ex:
					return jsonify({'error': 1, 'reason': 'An error occured: ' + str(type(ex)) + ": " + str(ex)})

				## ensure item is a file
				if not fstat.type == SMB_FILE:
					return jsonify({'error': 1, 'reason': 'You cannot stat a directory!'})

				# guess mimetype
				(ftype, mtype) = bargate.lib.mime.filename_to_mimetype(entry_name)

				data = {
					'filename': entry_name,
					'size':     fstat.size,
					'atime':    ut_to_string(fstat.atime),
					'mtime':    ut_to_string(fstat.mtime),
					'ftype':    ftype,
					'mtype':    mtype,
					'owner':    "N/A",
					'group':    "N/A",
				}

				try:
					data['owner'] = libsmbclient.getxattr(uri,smbc.XATTR_OWNER)
					data['group'] = libsmbclient.getxattr(uri,smbc.XATTR_GROUP)

					if app.config['WBINFO_LOOKUP']:
						data['owner'] = wb_sid_to_name(data['owner'])
						data['group'] = wb_sid_to_name(data['group'])
				except Exception as ex:
					pass

				return jsonify(data)

	################################################################################
	# BROWSE / DIRECTORY / LIST FILES
	################################################################################
		
			elif action == 'browse':
				if 'q' in request.args:

					if not app.config['SEARCH_ENABLED']:
						abort(404)

					## Build a breadcrumbs trail ##
					crumbs = []
					parts = path.split('/')
					b4 = ''

					## Build up a list of dicts, each dict representing a crumb
					for crumb in parts:
						if len(crumb) > 0:
							crumbs.append({'name': crumb, 'url': url_for(func_name,path=b4+crumb)})
							b4 = b4 + crumb + '/'

					query = request.args.get('q')
					self._init_search(libsmbclient,func_name,path,srv_path,query)
					results, timeout_reached = self._search()

					return render_template('search.html',
						timeout_reached = timeout_reached,
						results=results,
						query=query,
						path=path,
						root_display_name = display_name,
						search_mode=True,
						browse_mode=False,
						browse_butts_enabled=False,
						bmark_enabled=False,
						url_home=url_for(func_name),
						crumbs=crumbs,
					)

				elif 'xhr' in request.args:
					try:
						directory_entries = libsmbclient.ls(uri)
					except smbc.NotDirectoryError as ex:
						return bargate.lib.errors.stderr("Bargate is misconfigured","The path given for the share " + func_name + " is not a directory!")
					except Exception as ex:
						return self.smb_error(ex)

					dirs   = []
					files  = []
					shares = []

					for dentry in directory_entries:
						entry = self._direntry_load(dentry, srv_path, path)

						if not entry['skip']:
							entry = self._direntry_process(entry,libsmbclient,func_name)

							if entry['type'] == SMB_FILE:
								files.append(entry)
							elif entry['type'] == SMB_DIR:
								dirs.append(entry)
							elif entry['type'] == SMB_SHARE:
								shares.append(entry)

					bmark_enabled        = False
					browse_butts_enabled = False
					no_items             = False
					crumbs               = []

					if len(shares) == 0:
						## are there any items?
						if len(files) == 0 and len(dirs) == 0:
							no_items = True

						# only allow bookmarking if we're not at the root
						if len(path) > 0:
							bmark_enabled = True

						browse_butts_enabled = True

						## Build a breadcrumbs trail ##
						parts = path.split('/')
						b4    = ''

						## Build up a list of dicts, each dict representing a crumb
						for crumb in parts:
							if len(crumb) > 0:
								crumbs.append({'name': crumb, 'url': url_for(func_name,path=b4+crumb)})
								b4 = b4 + crumb + '/'

					return render_template('directory-' + bargate.lib.userdata.get_layout() + '.html',
						active=active,
						dirs=dirs,
						files=files,
						shares=shares,
						crumbs=crumbs,
						path=path,
						url_home=url_for(func_name),
						url_bookmark=url_for('bookmarks'),
						url_search=url_for(func_name,path=path,action="search"),
						browse_mode=True,
						browse_butts_enabled=browse_butts_enabled,
						bmark_enabled=bmark_enabled,
						func_name = func_name,
						root_display_name = display_name,
						no_items = no_items,
					)
				else:
					return render_template('browse.html',path=path,browse_mode=True,url=url_for(func_name,path=path))

			else:
				abort(400)

		############################################################################
		## HTTP POST ACTIONS #######################################################
		# actions: unlink, mkdir, upload, rename
		############################################################################

		elif request.method == 'POST':
			###############################
			# POST: UPLOAD
			###############################
			if action == 'upload':
		
				ret = []
			
				uploaded_files = request.files.getlist("files[]")
			
				for ufile in uploaded_files:
			
					if banned_file(ufile.filename):
						ret.append({'name' : ufile.filename, 'error': 'Filetype not allowed'})
						continue
					
					## Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
					filename = secure_filename(ufile.filename)
					upload_uri = uri + '/' + filename

					## Check the new file name is valid
					try:
						check_name(filename)
					except ValueError as e:
						ret.append({'name' : ufile.filename, 'error': 'Filename not allowed'})
						continue
					
					## Check to see if the file exists
					fstat = None
					try:
						fstat = libsmbclient.stat(upload_uri)
					except smbc.NoEntryError:
						app.logger.debug("Upload filename of " + upload_uri + " does not exist, ignoring")
						## It doesn't exist so lets continue to upload
					except Exception as ex:
						#app.logger.error("Exception when uploading a file: " + str(type(ex)) + ": " + str(ex) + traceback.format_exc())
						ret.append({'name' : ufile.filename, 'error': 'Failed to stat existing file: ' + str(ex)})
						continue

					byterange_start = 0
					if 'Content-Range' in request.headers:
						byterange_start = int(request.headers['Content-Range'].split(' ')[1].split('-')[0])
						app.logger.debug("Chunked file upload request: Content-Range sent with byte range start of " + str(byterange_start) + " with filename " + filename)

					## Actual upload
					try:
						# Check if we're writing from the start of the file
						if byterange_start == 0:
							## We're truncating an existing file, or creating a new file
							## If the file already exists, check to see if we should overwrite
							if fstat is not None:
								if not bargate.lib.userdata.get_overwrite_on_upload():
									ret.append({'name' : ufile.filename, 'error': 'File already exists. You can enable overwriting files in Settings.'})
									continue

								## Now ensure we're not trying to upload a file on top of a directory (can't do that!)
								itemType = self.etype(libsmbclient,upload_uri)
								if itemType == SMB_DIR:
									ret.append({'name' : ufile.filename, 'error': "That name already exists and is a directory"})
									continue

							## Open the file for the first time, truncating or creating it if necessary
							app.logger.debug("Opening for writing with O_CREAT and TRUNC")
							wfile = libsmbclient.open(upload_uri,os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
						else:
							## Open the file and seek to where we are going to write the additional data
							app.logger.debug("Opening for writing with O_WRONLY")
							wfile = libsmbclient.open(upload_uri,os.O_WRONLY)
							wfile.seek(byterange_start)

						while True:
							buff = ufile.read(io.DEFAULT_BUFFER_SIZE)
							if not buff:
								break
							wfile.write(buff)

						wfile.close()
						ret.append({'name' : ufile.filename})

					except Exception as ex:
						#app.logger.error("Exception when uploading a file: " + str(type(ex)) + ": " + str(ex) + traceback.format_exc())
						ret.append({'name' : ufile.filename, 'error': 'Could not upload file: ' + str(ex)})
						continue
					
				return jsonify({'files': ret})

			###############################
			# POST: RENAME
			###############################
			elif action == 'rename':

				try:
					old_name = request.form['old_name']
					new_name = request.form['new_name']
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Invalid parameter(s)'})

				## Check the new file name is valid
				try:
					check_name(new_name)
				except ValueError as e:
					return jsonify({'code': 1, 'msg': 'The new name is invalid'})

				## Build paths
				old_path = uri + "/" + old_name
				new_path = uri + "/" + new_name

				## get the item type of the existing 'filename'
				fstat = libsmbclient.stat(old_path)

				if fstat.type == SMB_FILE:
					typestr = "file"
				elif fstat.type == SMB_DIR:
					typestr = "directory"
				else:
					return bargate.lib.errors.invalid_item_type()

				try:
					libsmbclient.rename(old_path,new_path)
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Unable to rename: ' + str(type(ex))})
				else:
					return jsonify({'code': 0, 'msg': "The " + typestr + " '" + old_name + "' was renamed to '" + new_name + "' successfully"})

			###############################
			# POST: COPY
			###############################
			elif action == 'copy':

				try:
					src  = request.form['src']
					dest = request.form['dest']
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Invalid parameter(s)'})

				## check the proposed new name is valid
				try:
					check_name(dest)
				except ValueError as e:
					return jsonify({'code': 1, 'msg': 'The new name is invalid'})

				## Build paths
				src_path  = uri + "/" + src
				dest_path = uri + "/" + dest

				try:
					source_stat = libsmbclient.stat(src_path)
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'The file you tried to copy does not exist or could not be read'})

				if not source_stat.type == SMB_FILE:
					return jsonify({'code': 1, 'msg': 'Unable to copy a directory!'})

				## Make sure the dest file doesn't exist
				try:
					libsmbclient.stat(dest_path)
				except smbc.NoEntryError as ex:
					## This is what we want - i.e. no file/entry
					pass
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'The destination filename already exists'})

				## Assuming we got here without an exception, open the source file
				try:		
					source_fh = libsmbclient.open(src_path)
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Could not read from the source file'})

				## Assuming we got here without an exception, open the dest file
				try:
					dest_fh = libsmbclient.open(dest_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC )
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Could not write to the new file'})

				## copy the data in 1024 byte chunks
				try:
					location = 0
					while(location >= 0 and location < source_stat.size):
						chunk = source_fh.read(1024)
						dest_fh.write(chunk)
						location = source_fh.seek(1024,location)

				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Could not write to the new file'})

				return jsonify({'code': 0, 'msg': 'A copy of "' + src + '" was created as "' + dest + '"'})


			###############################
			# POST: MAKE DIRECTORY
			###############################
			elif action == 'mkdir':
				try:
					dirname = request.form['name']
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Invalid parameter'})

				## check the proposed new name is valid
				try:
					check_name(dirname)
				except ValueError as e:
					return jsonify({'code': 1, 'msg': 'That directory name is invalid'})

				try:
					libsmbclient.mkdir(uri + '/' + dirname)
				except Exce/ption as ex:
					return jsonify({'code': 1, 'msg': 'The file server returned an error when asked to create the directory'})

				return jsonify({'code': 0, 'msg': "The folder '" + dirname + "' was created successfully."})

			###############################
			# POST: DELETE
			###############################
			elif action == 'delete':
				try:
					delete_name = request.form['name']
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Invalid parameter'})

				delete_path  = uri + "/" + delete_name

				fstat = libsmbclient.stat(delete_path)

				if fstat.type == SMB_FILE:
					try:
						libsmbclient.delete(delete_path)
					except Exception as ex:
						return jsonify({'code': 1, 'msg': 'The file server returned an error when asked to delete the file'})
					else:
						return jsonify({'code': 0, 'msg': "The file '" + delete_name + "' was deleted"})

				elif fstat.type == SMB_DIR:
					try:
						libsmbclient.rmdir(delete_path)
					except Exception as ex:
						return jsonify({'code': 1, 'msg': 'The file server returned an error when asked to delete the directory'})
					else:
						return jsonify({'code': 0, 'msg': "The directory '" + delete_name + "' was deleted"})
				else:
					return jsonify({'code': 1, 'msg': 'You tried to delete something other than a file or directory'})

			###############################
			# POST: BOOKMARK
			###############################
			elif action == 'bookmark':

				try:
					bookmark_name     = request.form['name']
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Invalid parameter'})

				try:
					## Generate a unique identifier for this bookmark
					bookmark_id = uuid.uuid4().hex

					## Turn this into a redis key for the new bookmark
					redis_key = 'user:' + session['username'] + ':bookmark:' + bookmark_id

					## Store all the details of this bookmark in REDIS
					g.redis.hset(redis_key,'version','2')
					g.redis.hset(redis_key,'function', func_name)
					g.redis.hset(redis_key,'path',path)
					g.redis.hset(redis_key,'name',bookmark_name)

					## if we're on a custom server then we need to store the URL 
					## to that server otherwise the bookmark is useless.
					if func_name == 'custom':
						if 'custom_uri' in session:
							g.redis.hset(redis_key,'custom_uri',session['custom_uri'])
						else:
							return jsonify({'code': 1, 'msg': 'Invalid request'})

					## add the new bookmark name to the list of bookmarks for the user
					g.redis.sadd('user:' + session['username'] + ':bookmarks',bookmark_id)

					return jsonify({'code': 0, 'msg': 'Added bookmark ' + bookmark_name, 'url': url_for('bookmark',bookmark_id=bookmark_id)})

				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Could not save bookmark: ' + str(type(ex)) + " " + str(ex)})

			else:
				return jsonify({'code': 1, 'msg': "An invalid action was specified"})

	############################################################################

################################################################################

	def _init_search(self,libsmbclient,func_name,path,srv_path,query):
		self.libsmbclient = libsmbclient
		self.func_name    = func_name
		self.path         = path
		self.srv_path     = srv_path
		self.query        = query

		self.timeout_reached = False
		self.results         = []

	def _search(self):
		self.timeout_at = int(time.time()) + app.config['SEARCH_TIMEOUT']
		self._rsearch(self.path)
		return (self.results, self.timeout_reached)

	def _rsearch(self,path):
		## Try getting directory contents of where we are
		app.logger.debug("_rsearch called to search: " + path)
		try:
			directory_entries = self.libsmbclient.ls(self.srv_path + "/" + path)
		except smbc.NotDirectoryError as ex:
			return

		except Exception as ex:
			app.logger.info("Search encountered an exception " + str(ex) + " " + str(type(ex)))
			return

		## now loop over each entry
		for dentry in directory_entries:

			## don't keep searching if we reach the timeout
			if self.timeout_reached:
				break;
			elif int(time.time()) >= self.timeout_at:
				self.timeout_reached = True
				break

			entry = self._direntry_load(dentry, self.srv_path, path)

			## Skip hidden files
			if entry['skip']:
				continue

			## Check if the filename matched
			if self.query.lower() in entry['name'].lower():
				app.logger.debug("_rsearch: Matched: " + entry['name'])
				entry = self._direntry_process(entry, self.libsmbclient, self.func_name)
				entry['parent_path'] = path
				entry['parent_url']  = url_for(self.func_name,path=path)
				self.results.append(entry)

			## Search subdirectories if we found one
			if entry['type'] == SMB_DIR:
				if len(path) > 0:
					sub_path = path + "/" + entry['name']
				else:
					sub_path = entry['name']

				self._rsearch(sub_path)

	############################################################################

	def _direntry_load(self,dentry,srv_path, path):
		entry = {'skip': False, 'name': dentry.name}

		# old versions of pysmbc return 'str' objects rather than unicode
		if isinstance(entry['name'], str):
			entry['name'] = entry['name'].decode("utf-8")

		## Skip entries for 'this dir' and 'parent dir'
		if entry['name'] == '.' or entry['name'] == '..':
			entry['skip'] = True

		## Build the entire URI
		entry['uri'] = srv_path + path + '/' + entry['name']

		## Build the path
		if len(path) == 0:
			entry['path'] = entry['name']
		else:
			entry['path'] = path + '/' + entry['name']

		## hide files which we consider 'hidden'
		if not bargate.lib.userdata.get_show_hidden_files():
			if entry['name'].startswith('.'):
				entry['skip'] = True
			if entry['name'].startswith('~$'):
				entry['skip'] = True
			if entry['name'] in ['desktop.ini', '$RECYCLE.BIN', 'RECYCLER', 'Thumbs.db']:
				entry['skip'] = True

		if dentry.smbc_type in [SMB_FILE, SMB_DIR, SMB_SHARE]:
			entry['type'] = dentry.smbc_type

			if dentry.smbc_type == SMB_SHARE:
				if entry['name'].endswith == "$":
					entry['skip'] = True

		else:
			entry['type'] = SMB_OTHER
			entry['skip'] = True

		return entry

################################################################################

	def _direntry_process(self,entry,libsmbclient,func_name):
		if entry['type'] == SMB_FILE:
			## Generate 'mtype', 'mtype_raw' and 'icon'
			entry['icon'] = 'fa fa-fw fa-file-text-o'
			(entry['mtype'],entry['mtype_raw']) = bargate.lib.mime.filename_to_mimetype(entry['name'])
			entry['icon'] = bargate.lib.mime.mimetype_to_icon(entry['mtype_raw'])

			## Generate URLs to this file
			entry['stat']         = url_for(func_name,path=entry['path'],action='stat')
			entry['download']     = url_for(func_name,path=entry['path'],action='download')

			try:
				fstat = libsmbclient.stat(entry['uri'])
			except Exception as ex:
				## If the file stat failed we return a result with the data missing
				## rather than fail the entire page load
				entry['mtime_raw'] = 0
				entry['mtime'] = "Unknown"
				entry['size'] = 0
				entry['error'] = True
				return entry

			entry['mtime_raw'] = fstat.mtime
			entry['mtime']     = ut_to_string(fstat.mtime)
			entry['size']      = fstat.size

			## Image previews
			if app.config['IMAGE_PREVIEW'] and entry['mtype_raw'] in bargate.lib.mime.pillow_supported:
				if fstat.size <= app.config['IMAGE_PREVIEW_MAX_SIZE']:
					entry['img_preview'] = url_for(func_name,path=entry['path'],action='preview')
			else:
				entry['size'] = 0

			## View-in-browser download type
			if bargate.lib.mime.view_in_browser(entry['mtype_raw']):
				entry['view'] = url_for(func_name,path=entry['path'],action='view')

		elif entry['type'] == SMB_DIR:
			entry['stat'] = url_for(func_name,path=entry['path'],action='stat')
			entry['url']  = url_for(func_name,path=entry['path'])

		elif entry['type'] == SMB_SHARE:
			entry['url'] = url_for(func_name,path=entry['path'])

		return entry

	############################################################################
	############################################################################

	def smb_error_info(self,ex):

		if isinstance(ex,smbc.PermissionError):
			return ("Permission Denied","You do not have permission to perform the action")

		elif isinstance(ex,smbc.NoEntryError):
			return ("No such file or directory","The file or directory was not found")

		elif isinstance(ex,smbc.NoSpaceError):
			return ("No space left on device","There is no space left on the server. You may have exceeded your usage allowance")

		elif isinstance(ex,smbc.ExistsError):
			return ("File or directory already exists","The file or directory you attempted to create already exists")

		elif isinstance(ex,smbc.NotEmptyError):
			return ("The directory is not empty","The directory is not empty so cannot be deleted")

		elif isinstance(ex,smbc.TimedOutError):
			return ("Timed out","The current operation timed out. Please try again later")

		elif isinstance(ex,smbc.ConnectionRefusedError):
			return self.smbc_ConnectionRefusedError()
		
		# pysmbc spits out RuntimeError when everything else fails
		elif isinstance(ex,RuntimeError):
			return ("File Server Error","An unknown error was returned from the file server. Please contact your support team")

		# ALL OTHER EXCEPTIONS
		else:
			return ("Internal error",str(type(ex)) + " - " + str(ex))

	def smb_error(self,ex):
		(title, desc) = self.smb_error_info(ex)
		return stderr(title,desc)

