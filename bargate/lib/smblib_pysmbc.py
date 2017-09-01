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
import string, os, io, smbc, sys, stat, pprint, urllib, re
from flask import Flask, send_file, request, session, g, redirect, url_for
from flask import abort, flash, make_response, jsonify, render_template
import bargate.lib.core
import bargate.lib.errors
import bargate.lib.userdata
import bargate.lib.mime

### Python imaging stuff
from PIL import Image
import glob
import StringIO

import traceback

#### SMB entry types
SMB_ERR         = -1
SMB_WORKGROUP   = 1
SMB_SERVER      = 2
SMB_SHARE       = 3
SMB_PRINTER     = 4
SMB_COMMS_SHARE = 5
SMB_IPC         = 6
SMB_DIR         = 7
SMB_FILE        = 8
SMB_LINK        = 9

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
		url = self._convert(url)
		return self.smbclient.stat(url)

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

	def _estat(self,libsmbclient,url):
		"""Run stat() on a URI and return a dictionary with friendly named keys"""

		# Strip off trailing slashes as they're useless to us
		if url.endswith('/'):
			url = url[:-1]

		fstat = libsmbclient.stat(url)

		return {'mode':  fstat[0], 	## unix mode
				'ino':   fstat[1], 	## inode number
				'dev':   fstat[2], 	## device number
				'nlink': fstat[3],	## number of links
				'uid':   fstat[4], 	## user ID
				'gid':   fstat[5], 	## group ID
				'size':  fstat[6], 	## size in bytes
				'atime': fstat[7],	## access time
				'mtime': fstat[8],	## modify time
				'ctime': fstat[9]	## change time
		}

################################################################################

	def _etype(self,libsmbclient,uri):
		## stat the file, st_mode has all the info we need

		## Strip off trailing slashes as they're useless to us
		if uri.endswith('/'):
			uri = uri[:-1]

		## stat the URI
		try:
			fstat = libsmbclient.stat(uri)
		except Exception as ex:
			return bargate.lib.errors.smbc_handler(ex,uri)

		return self._stype(fstat)

################################################################################

	def _stype(self,fstat):

		## get st_mode out of the stat tuple
		st_mode = fstat[0]

		## DIRECTORY
		if stat.S_ISDIR(st_mode):
			return SMB_DIR
		elif stat.S_ISREG(st_mode):
			return SMB_FILE	
		elif stat.S_ISLNK(st_mode):
			return SMB_LINK
		else:
			return -1

################################################################################

	def _direntry_load(self,dentry,srv_path, path):
		"""This function takes a directory entry returned from getdents and returns
			a dictionary of information about the dentry. Its primary purpose is
			to return unicode and str objects for the name, path and URI of the entry
			and determine if the entry should be 'skipped'.

			'skip' means the file should be omitted from results because either 
			it is '.' or '..' or is considered a 'hidden' file.

			The dictionary returned contains the following keys:

				- type			Either 'file', 'dir', 'share' or 'other'
				- name			The entry name
				- uri			The full URI including smb:// to the entry as a str object
				- path			The full path (not including smb:// and  the server name) to the entry as a unicode object
				- skip			Should this entry be shown to the user or not
			"""

		entry = {'skip': False, 'name': dentry.name}

		# old versions of pysmbc return 'str' objects rather than unicode
		if isinstance(entry['name'], str):
			entry['name'] = entry['name'].decode("utf-8")

		## Skip entries for 'this dir' and 'parent dir'
		if entry['name'] == '.':
			entry['skip'] = True
		if entry['name'] == '..':
			entry['skip'] = True

		## Build the entire URI (str object)
		entry['uri'] = srv_path + path + '/' + entry['name']

		## Build the path (unicode object)
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

		if dentry.smbc_type == SMB_FILE:
			entry['type'] = 'file'
		elif dentry.smbc_type == SMB_DIR:
			entry['type'] = 'dir'
		elif dentry.smbc_type == SMB_SHARE:
			entry['type'] = 'share'
			if entry['name'].endswith == "$":
				entry['skip'] = True
		else:
			entry['type'] = 'other'
			entry['skip'] = True

		return entry

################################################################################

	def _direntry_process(self,entry,libsmbclient,func_name):
		"""This function takes a directory entry returned from the _direntry_load
			function (a dictionary) and performs further processing on the dentry 
			via stat() if its a file and infers information such as mimetype and 
			icon from the entry name. This is used by the browse function and also 
			by the search function (but only when it finds a matching filename).

			The dictionary returned contains the following ADDITIONAL keys:

				For all types:
				- icon			The CSS class names to use as the icon

				For files and directories:
				- stat			The URL to 'stat' the entry further (an AJAX/JSON call)			
				- open			The URL to 'open' the file/directory

				For files only:
				- mtype			The friendly 'file type' string e.g. Microsoft Word Document
				- mtype_raw		The raw mimetype e.g. text/plain
				- download		The URL to 'download' the file
				- size			Size of the file in bytes
				- mtime			The modify time of the file as a friendly string
				- mtime_raw 	The modify time of the file as a UNIX timestamp

				For files that should be 'viewed' in browser:
				- view			The URL to 'view' the file

				For image files that should be previewed:
				- img_preview	The URL to the image for previews
			"""

		if entry['type'] == 'file':
			## Generate 'mtype', 'mtype_raw' and 'icon'
			entry['icon'] = 'fa fa-fw fa-file-text-o'
			(entry['mtype'],entry['mtype_raw']) = bargate.lib.mime.filename_to_mimetype(entry['name'])
			entry['icon'] = bargate.lib.mime.mimetype_to_icon(entry['mtype_raw'])

			## Generate URLs to this file
			entry['stat']         = url_for(func_name,path=entry['path'],action='stat')
			entry['download']     = url_for(func_name,path=entry['path'],action='download')

			try:

				## For files we stat the file and look up a bunch of stuff
				fstat = self._estat(libsmbclient,entry['uri'])
			except Exception as ex:
				## If the file stat failed we return a result with the data missing
				## rather than fail the entire page load
				entry['mtime_raw'] = 0
				entry['mtime'] = "Unknown"
				entry['size'] = 0
				entry['error'] = True
				return entry

			if 'mtime' in fstat:
				entry['mtime_raw'] = fstat['mtime']
				entry['mtime']     = bargate.lib.core.ut_to_string(fstat['mtime'])
			else:
				entry['mtime']     = 'Unknown'
				entry['mtime_raw'] = 0

			if 'size' in fstat:
				entry['size'] = fstat['size']

				## Image previews
				if app.config['IMAGE_PREVIEW'] and entry['mtype_raw'] in bargate.lib.mime.pillow_supported:
					if int(fstat['size']) <= app.config['IMAGE_PREVIEW_MAX_SIZE']:
						entry['img_preview'] = url_for(func_name,path=entry['path'],action='preview')
			else:
				entry['size'] = 0

			## View-in-browser download type
			if bargate.lib.mime.view_in_browser(entry['mtype_raw']):
				entry['view'] = url_for(func_name,path=entry['path'],action='view')

		elif entry['type'] == 'dir':
			entry['stat'] = url_for(func_name,path=entry['path'],action='stat')
			entry['url']  = url_for(func_name,path=entry['path'])

		elif entry['type'] == 'share':
			entry['url'] = url_for(func_name,path=entry['path'])

		return entry

################################################################################

	def smb_action(self,srv_path,func_name,active=None,display_name="Home",action='browse',path=''):

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
			return bargate.lib.errors.stderr("Invalid server path","The server URL must start with smb://")

		## Check the path is valid
		try:
			bargate.lib.core.check_path(path)
		except ValueError as e:
			return bargate.lib.errors.invalid_path()

		## Build the URI
		uri        = srv_path + path

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
					fstat    = libsmbclient.stat(uri)
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)

				## ensure item is a file
				if not self._stype(fstat) == SMB_FILE:
					return bargate.lib.errors.invalid_item_download()

				try:
					file_object = libsmbclient.open(uri)

					## Default to sending files as an 'attachment' ("Content-Disposition: attachment")
					attach = True

					## Guess the mime type  based on file extension
					(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entry_name)

					## If the user requested to 'view' (don't download as an attachment) make sure we allow it for that filetype
					if action == 'view':
						if bargate.lib.mime.view_in_browser(mtype):
							attach = False

					## Send the file to the user
					resp = make_response(send_file(file_object,add_etags=False,as_attachment=attach,attachment_filename=entry_name,mimetype=mtype))
					resp.headers['content-length'] = str(fstat[6])
					return resp
	
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)

	################################################################################
	# IMAGE PREVIEW
	################################################################################
		
			elif action == 'preview':
				if not app.config['IMAGE_PREVIEW']:
					abort(400)

				try:
					fstat = libsmbclient.stat(uri)
				except Exception as ex:
					abort(400)

				## ensure item is a file
				if not self._stype(fstat) == SMB_FILE:
					abort(400)
				
				## guess a mimetype
				(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entry_name)
			
				## Check size is not too large for a preview
				if fstat[6] > app.config['IMAGE_PREVIEW_MAX_SIZE']:
					abort(403)

				## Only preview files that Pillow supports
				if not mtype in bargate.lib.mime.pillow_supported:
					abort(400)

				## Open the file
				try:
					file_object = libsmbclient.open(uri)
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)
			
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

				data = {}	
				data['filename']              = entry_name
				data['size']                  = fstat[6]
				data['atime']                 = bargate.lib.core.ut_to_string(fstat[7])
				data['mtime']                 = bargate.lib.core.ut_to_string(fstat[8])
				(data['ftype'],data['mtype']) = bargate.lib.mime.filename_to_mimetype(data['filename'])
			
				if app.config['WBINFO_LOOKUP']:
					try:
						data['owner'] = bargate.lib.core.wb_sid_to_name(libsmbclient.getxattr(uri,smbc.XATTR_OWNER))
						data['group'] = bargate.lib.core.wb_sid_to_name(libsmbclient.getxattr(uri,smbc.XATTR_GROUP))
					except Exception as ex:
						data['owner'] = "Unknown"
						data['group'] = "Unknown"
				else:
					data['owner'] = "N/A"
					data['group'] = "N/A"

				data['error'] = 0

				## Return JSON
				return jsonify(data)

	################################################################################
	# REALLY REALLY BASIC SEARCH...
	################################################################################
			
			elif action == 'search':
				if not app.config['SEARCH_ENABLED']:
					abort(404)

				if 'q' not in request.args:
					return redirect(url_for(func_name,path=path))

				## Build a breadcrumbs trail ##
				crumbs = []
				parts = path.split('/')
				b4 = ''

				## Build up a list of dicts, each dict representing a crumb
				for crumb in parts:
					if len(crumb) > 0:
						crumbs.append({'name': crumb, 'url': url_for(func_name,path=b4+crumb)})
						b4 = b4 + crumb + '/'

				query   = request.args.get('q')

				self._init_search(libsmbclient,func_name,path,srv_path,uri,query)
				results, timeout_reached = self._search()

				if timeout_reached:
					flash("Some search results have been omitted because the search took too long to perform.","alert-warning")

				return render_template('search.html',
					results=results,
					query=query,
					path=path,
					root_display_name = display_name,
					search_mode=True,
					url_home=url_for(func_name),
					crumbs=crumbs,
				)
			
	################################################################################
	# BROWSE / DIRECTORY / LIST FILES
	################################################################################
		
			elif action == 'browse':
				if 'q' in request.args:
					# TODO search
					pass
				elif 'xhr' in request.args:

					## Try getting directory contents
					try:
						directory_entries = libsmbclient.ls(uri)
					except smbc.NotDirectoryError as ex:
						return bargate.lib.errors.stderr("Bargate is misconfigured","The path given for the share " + func_name + " is not a directory!")
					except Exception as ex:
						return bargate.lib.errors.smbc_handler(ex,uri)

					dirs   = []
					files  = []
					shares = []

					for dentry in directory_entries:
						entry = self._direntry_load(dentry, srv_path, path)

						if entry['skip']:
							continue
						else:
							entry = self._direntry_process(entry,libsmbclient,func_name)

							if entry['type'] == 'file':
								files.append(entry)
							elif entry['type'] == 'dir':
								dirs.append(entry)
							elif entry['type'] == 'share':
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

			## We ignore an action and/or path sent in the URL
			## this is because we send them both via form variables
			## we do this because we need, in javascript, to be able to change these
			## without having to regenerate the URL in the <form>
			## as such, the path and action are not sent via bargate POSTs anyway

			## Get the action and path
			path   = request.form['path']
		
	################################################################################
	# UPLOAD FILE
	################################################################################

			if action == 'jsonupload':
		
				ret = []
			
				uploaded_files = request.files.getlist("files[]")
			
				for ufile in uploaded_files:
			
					if bargate.lib.core.banned_file(ufile.filename):
						ret.append({'name' : ufile.filename, 'error': 'Filetype not allowed'})
						continue
					
					## Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
					filename = bargate.lib.core.secure_filename(ufile.filename)
					upload_uri = uri + '/' + filename

					## Check the new file name is valid
					try:
						bargate.lib.core.check_name(filename)
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

	################################################################################
	# RENAME FILE
	################################################################################

			elif action == 'rename':

				## Get the new requested file name
				new_filename = request.form['newfilename']

				## Check the new file name is valid
				try:
					bargate.lib.core.check_name(new_filename)
				except ValueError as e:
					return bargate.lib.errors.invalid_name()

				## build new URI
				if parent_directory:
					new_uri = srv_path + parent_directory_path + '/' + new_filename
				else:
					new_uri = srv_path + new_filename

				## get the item type of the existing 'filename'
				itemType = self._etype(libsmbclient,uri)

				if itemType == SMB_FILE:
					typemsg = "The file"
				elif itemType == SMB_DIR:
					typemsg = "The directory"
				else:
					return bargate.lib.errors.invalid_item_type()

				try:
					libsmbclient.rename(uri,new_uri)
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)
				else:
					flash(typemsg + " '" + entry_name + "' was renamed to '" + request.form['newfilename'] + "' successfully.",'alert-success')
					return parent_redirect

	################################################################################
	# COPY FILE
	################################################################################

			elif action == 'copy':

				try:
					## stat the source file first
					source_stat = libsmbclient.stat(uri)

					## size of source
					source_size = source_stat[6]

					## determine item type
					itemType = self._stype(source_stat)

					## ensure item is a file
					if not itemType == SMB_FILE:
						return bargate.lib.errors.invalid_item_copy()

				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)

				## Get the new filename
				dest_filename = request.form['filename']
			
				## Check the new file name is valid
				try:
					bargate.lib.core.check_name(request.form['filename'])
				except ValueError as e:
					return bargate.lib.errors.invalid_name()
			
				if parent_directory:
					dest = srv_path + parent_directory_path + '/' + dest_filename
				else:
					dest = srv_path + dest_filename

				## Make sure the dest file doesn't exist
				try:
					libsmbclient.stat(dest)
				except smbc.NoEntryError as ex:
					## This is what we want - i.e. no file/entry
					pass
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)

				## Assuming we got here without an exception, open the source file
				try:		
					source_fh = libsmbclient.open(uri)
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)

				## Assuming we got here without an exception, open the dest file
				try:		
					dest_fh = libsmbclient.open(dest, os.O_CREAT | os.O_WRONLY | os.O_TRUNC )

				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,srv_path + dest)

				## try reading then writing blocks of data, then redirect!
				try:
					location = 0
					while(location >= 0 and location < source_size):
						chunk = source_fh.read(1024)
						dest_fh.write(chunk)
						location = source_fh.seek(1024,location)

				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,srv_path + dest)

				flash('A copy of "' + entry_name + '" was created as "' + dest_filename + '"','alert-success')
				return parent_redirect

	################################################################################
	# MAKE DIR
	################################################################################

			elif action == 'mkdir':
				## Check the path is valid
				try:
					bargate.lib.core.check_name(request.form['directory_name'])
				except ValueError as e:
					return bargate.lib.errors.invalid_name()

				mkdir_uri = uri + '/' + request.form['directory_name']

				try:
					libsmbclient.mkdir(mkdir_uri,0755)
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri)
				else:
					flash("The folder '" + request.form['directory_name'] + "' was created successfully.",'alert-success')
					return redirect(url_for(func_name,path=path))

	################################################################################
	# DELETE FILE
	################################################################################

			elif action == 'unlink':
				## get the item type of the entry we've been asked to delete
				itemType = self._etype(libsmbclient,uri)

				if itemType == SMB_FILE:
					try:
						libsmbclient.unlink(uri)
					except Exception as ex:
						return bargate.lib.errors.smbc_handler(ex,uri)
					else:
						flash("The file '" + entry_name + "' was deleted successfully.",'alert-success')
						return parent_redirect

				elif itemType == SMB_DIR:
					try:
						libsmbclient.rmdir(uri)
					except Exception as ex:
						return bargate.lib.errors.smbc_handler(ex,uri)
					else:
						flash("The directory '" + entry_name + "' was deleted successfully.",'alert-success')
						return parent_redirect
				else:
					return bargate.lib.errors.invalid_item_type()

			else:
				abort(400)

	############################################################################

################################################################################

	def _init_search(self,libsmbclient,func_name,path,srv_path,uri,query):
		self.libsmbclient    = libsmbclient
		self.func_name       = func_name
		self.path            = path
		self.path_as_str     = path_as_str
		self.srv_path_as_str = srv_path_as_str
		self.uri_as_str      = uri_as_str
		self.query           = query

		self.timeout_at      = int(time.time()) + app.config['SEARCH_TIMEOUT']
		self.timeout_reached = False
		self.results         = []

	def _search(self):
		self._rsearch(self.path,self.path_as_str,self.uri_as_str)
		return self.results, self.timeout_reached

	def _rsearch(self,path, path_as_str, uri_as_str):
		## Try getting directory contents of where we are
		app.logger.debug("_rsearch called to search: " + uri_as_str)
		try:
			directory_entries = self.libsmbclient.list(uri)
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

			entry = self._direntry_load(dentry, self.srv_path_as_str, path, path_as_str)

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
			if entry['type'] == 'dir':
				if len(path) > 0:
					new_path        = path + "/" + entry['name']
					new_path_as_str = path_as_str + "/" + entry['name_as_str']
				else:
					new_path        = entry['name']
					new_path_as_str = entry['name_as_str']					

				self._rsearch(new_path, new_path_as_str, entry['uri_as_str'])
