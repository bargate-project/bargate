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
import string, os, io, sys, stat, pprint, urllib, re, StringIO, glob, traceback, socket, tempfile
from flask import Flask, send_file, request, session, g, redirect, url_for, abort, flash, make_response, jsonify, render_template
import bargate.lib.core
import bargate.lib.errors
import bargate.lib.userdata
import bargate.lib.mime
import bargate.views.errors

from smb.SMBConnection import SMBConnection
from smb.base import SMBTimeout, NotReadyError, NotConnectedError
from smb.smb_structs import UnsupportedFeature, ProtocolError, OperationFailure
from PIL import Image

class backend_pysmb:
	def smb_error(self,exception_object,uri="Unknown",redirect_to=None):
		"""Handles exceptions generated by pysmb functions. It currently deals with
		all known smb exceptions. This will generate fancy formatted messages
		for each smb type.
		"""

		# pysmb exceptions
		if isinstance(exception_object,SMBTimeout):
			return self._exSMBTimeout(redirect_to)
		if isinstance(exception_object,NotReadyError):
			return self._exNotReadyError(redirect_to)
		if isinstance(exception_object,NotConnectedError):
			return self._exNotConnectedError(redirect_to)
		if isinstance(exception_object,UnsupportedFeature):
			return self._exUnsupportedFeature(redirect_to)
		if isinstance(exception_object,ProtocolError):
			return self._exProtocolError(redirect_to)
		if isinstance(exception_object,OperationFailure):
			#return self._exOperationFailure(redirect_to)
			return bargate.views.errors.error500(exception_object)

		# anything else
		else:
			return bargate.views.errors.error500(exception_object)

################################################################################

	def smb_action(self,srv_path,func_name,active=None,display_name="Home",action='browse',path=''):
		## If the method is POST then 'action' and 'path' are set in the form
		## rather than in the URL. We do this because we need, in javascript, 
		## to be able to change these without having to regenerate the URL in 
		## the <form> as such, the path and action are not sent via bargate 
		## POSTs anyway
		if request.method == 'POST':
			action = request.form['action']
			#path   = request.form['path']

		## ensure srv_path (the server URI and share) does not end with a trailing slash
		if srv_path.endswith('/'):
			srv_path = srv_path[:-1]

		## srv_path should always start with smb://
		if not srv_path.startswith("smb://"):
			return bargate.lib.errors.stderr("Invalid server path","The server URL must start with smb://")

		## work out just the server name part of the URL
		url_parts   = srv_path.replace("smb://","").split('/')
		server_name = url_parts[0]

		#flash("URL_PARTS: " + str(url_parts),"alert-info")

		if len(url_parts) == 1:
			## TODO support browse here, to show a list of shares
			return bargate.lib.errors.stderr("Invalid server path","The server URL must include at least a share name")
		else:
			share_name = url_parts[1]

			if len(url_parts) == 2:
				path_prefix = ""
			else:
				path_prefix = "/" + "/".join(url_parts[2:])

			if len(path_prefix) > 0:
				full_path = path_prefix + "/" + path
			else:
				full_path = path

		#flash("SERVER_NAME: " + unicode(server_name),"alert-info")
		#flash("SHARE NAME: " + unicode(share_name),"alert-info")
		#flash("FULL PATH: " + unicode(full_path),"alert-info")


		## default the 'active' variable to the function name
		if active == None:
			active = func_name

		## The place to redirect to (the url) if an error occurs
		## This defaults to None (aka don't redirect, and just show an error)
		## because to do otherwise will lead to a redirect loop. (Fix #93 v1.4.1)
		error_redirect = None

		## The parent directory to redirect to - defaults to just the current function
		## name (the handler for this 'share' at the top level)
		parent_redirect = redirect(url_for(func_name))

		## Work out if there is a parent directory
		## and work out the entry name (filename or directory name being browsed)
		if len(path) > 0:
			parent_directory = True

			(parent_directory_path,seperator,entry_name) = path.rpartition('/')
			## if seperator was not found then the first two strings returned will be empty strings
			if len(parent_directory_path) > 0:
				## update the parent redirect with the correct path
				parent_redirect = redirect(url_for(func_name,path=parent_directory_path))
				error_redirect  = parent_redirect
				full_parent_directory_path = path_prefix + "/" + parent_directory_path

			else:
				# there is a parent directory - the 'share' - so just set the parent 
				# path to empty, because share_name (the actual parent dir) is sent
				# as the first parameter with each call anyway
				parent_directory_path = ""
				full_parent_directory_path = path_prefix + ""

		else:
			# we're at the share root
			parent_directory = False
			parent_directory_path = ""
			full_parent_directory_path = path_prefix
			entry_name = ""

		uri = srv_path + "/" + path

		#app.logger.debug(u"srv_path: " + srv_path + "; " + unicode(type(server_name)))
		#app.logger.debug(u"server_name: " + server_name + "; " + unicode(type(server_name)))
		#app.logger.debug(u"share_name: " + share_name + "; " + unicode(type(share_name)))
		#app.logger.debug(u"path " + path + u"; " + unicode(type(path)))
		#app.logger.debug(u"full_path: " + full_path + "; " + unicode(type(full_path)))
		#app.logger.debug(u"uri: " + uri + "; " + unicode(type(uri)))
		#app.logger.debug(u"entry_name: " + entry_name + "; " + unicode(type(entry_name)))
		#app.logger.debug(u"parent_directory: " + unicode(parent_directory) + "; " + str(type(parent_directory)))
		#app.logger.debug(u"parent_directory_path: " + parent_directory_path + "; " + str(type(parent_directory_path)))
		#app.logger.debug(u"full_parent_directory_path: " + full_parent_directory_path + "; " + str(type(full_parent_directory_path)))

		## Check the path is valid
		try:
			bargate.lib.core.check_path(path)
		except ValueError as e:
			return bargate.lib.errors.invalid_path()

		## Connect to the SMB server
		conn = SMBConnection(session['username'], bargate.lib.user.get_password(), socket.gethostname(), server_name, domain=app.config['SMB_WORKGROUP'], use_ntlm_v2 = True, is_direct_tcp=True)

		if not conn.connect(server_name,port=445,timeout=5):
			return bargate.lib.errors.stderr("Could not connect","Could not connect to the SMB server, authentication was unsuccessful")

		## Log this activity
		app.logger.info('user: "' + session['username'] + '", svr_path: "' + srv_path + '", endpoint: "' + func_name + '", action: "' + action + '", method: ' + str(request.method) + ', path: "' + path + '", addr: "' + request.remote_addr + '", ua: ' + request.user_agent.string)

		#flash("SMB2: " + str(conn.isUsingSMB2),"alert-info")

		if request.method == 'GET':
			###############################
			# GET: DOWNLOAD OR 'VIEW' FILE
			###############################
			if action == 'download' or action == 'view':

				try:
					## Default to sending files as an 'attachment' ("Content-Disposition: attachment")
					attach = True

					try:
						sfile = conn.getAttributes(share_name,full_path)
					except Exception as ex:
						return bargate.lib.errors.stderr("Not found","The path you specified does not exist, or could not be read")

					## if we were asked to 'download' a directory, redirect to browse instead
					if sfile.isDirectory:
						return redirect(url_for(func_name,path=path))

					## guess a mimetype
					(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entry_name)

					## If the user requested to 'view' (don't download as an attachment) make sure we allow it for that filetype
					if action == 'view':
						if bargate.lib.mime.view_in_browser(mtype):
							attach = False

					## pysmb wants to write to a file, rather than provide a file-like object to read from. EUGH.
					## so we need to write to a temporary file that Flask's send_file can then read from.
					tfile = tempfile.SpooledTemporaryFile(max_size=1048576)

					## Read data into the tempfile via SMB
					conn.retrieveFile(share_name,full_path,tfile)
					## Seek back to 0 on the tempfile, otherwise send_file breaks (!)
					tfile.seek(0)

					## Send the file to the user
					resp = make_response(send_file(tfile,add_etags=False,as_attachment=attach,attachment_filename=entry_name,mimetype=mtype))
					resp.headers['Content-length'] = sfile.file_size
					return resp
	
				except Exception as ex:
					return self.smb_error(ex,uri,error_redirect)

			####################
			# GET: IMAGE PREVIEW
			####################
			elif action == 'preview':
				if not app.config['IMAGE_PREVIEW']:
					abort(400)

				try:
					sfile = conn.getAttributes(share_name,full_path)
				except Exception as ex:
					abort(400)

				## ensure item is a file
				if sfile.isDirectory:
					abort(400)
			
				## guess a mimetype
				(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entry_name)
		
				## Check size is not too large for a preview
				if sfile.file_size > app.config['IMAGE_PREVIEW_MAX_SIZE']:
					abort(403)
			
				## Only preview files that Pillow supports
				if not mtype in bargate.lib.mime.pillow_supported:
					abort(400)

				## read the file
				tfile = tempfile.SpooledTemporaryFile(max_size=1048576)
				conn.retrieveFile(share_name,full_path,tfile)
				tfile.seek(0)

				try:
					pil_img = Image.open(tfile).convert('RGB')
					size = 200, 200
					pil_img.thumbnail(size, Image.ANTIALIAS)

					ifile = StringIO.StringIO()
					pil_img.save(ifile, 'JPEG', quality=85)
					ifile.seek(0)
					return send_file(ifile, mimetype='image/jpeg',add_etags=False)
				except Exception as ex:
					abort(400)

			################################################
			# GET: STAT FILE (ajax call to get more details)
			################################################
			elif action == 'stat': 

				try:
					sfile = conn.getAttributes(share_name,full_path)
				except Exception as ex:
					return jsonify({'error': 1, 'reason': 'An error occured: ' + str(type(ex)) + ": " + str(ex)})

				## ensure item is a file
				if sfile.isDirectory:
					return jsonify({'error': 1, 'reason': 'You cannot stat a directory!'})

				data = {}	
				data['filename']              = sfile.filename
				data['size']                  = sfile.file_size
				data['atime']                 = bargate.lib.core.ut_to_string(sfile.last_access_time)
				data['mtime']                 = bargate.lib.core.ut_to_string(sfile.last_write_time)
				(data['ftype'],data['mtype']) = bargate.lib.mime.filename_to_mimetype(data['filename'])
				data['owner']                 = "Not yet implemented"
				data['group']                 = "Not yet implemented"
				data['error']                 = 0

				return jsonify(data)

			###############################
			# GET: SEARCH
			###############################
			elif action == 'search': #TODO
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

				self._init_search(libsmbclient,func_name,path,path_as_str,srv_path_as_str,uri_as_str,query)
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
					on_file_click=bargate.lib.userdata.get_on_file_click())
			
			###############################
			# GET: BROWSE / LS
			###############################
			elif action == 'browse':

 				return render_template('browse.html',path=path,browse_mode=True,url_here=url_for(func_name,path=path,action='xhr'))

			elif action == 'xhr':

				try:
					directory_entries = conn.listPath(share_name,full_path)
				except Exception as ex:
					return self.smb_error(ex,uri,error_redirect)

				## Seperate out dirs and files into two lists
				dirs  = []
				files = []

				# sfile = shared file (smb.base.SharedFile)
				for sfile in directory_entries:
					entry = self._sfile_load(sfile, srv_path, path, func_name)

					# Don't add hidden files
					if not entry['skip']:
						if entry['type'] == 'file':
							files.append(entry)
						elif entry['type'] == 'dir':
							dirs.append(entry)

				## Build a breadcrumbs trail ##
				crumbs = []
				parts  = path.split('/')
				b4     = ''

				## Build up a list of dicts, each dict representing a crumb
				for crumb in parts:
					if len(crumb) > 0:
						crumbs.append({'name': crumb, 'jurl': url_for(func_name,action="xhr",path=b4+crumb), 'url': url_for(func_name,path=b4+crumb)})
						b4 = b4 + crumb + '/'

				## Are we at the root?
				if len(path) == 0:
					atroot = True
				else:
					atroot = False
				
				## are there any items in the list?
				no_items = False
				if len(files) == 0 and len(dirs) == 0:
					no_items = True

				## What layout mode does the user want?
				layout = bargate.lib.userdata.get_layout()

				## Render the template
				return render_template('directory-' + layout + '.html',
					active=active,
					dirs=dirs,
					files=files,
					crumbs=crumbs,
					path=path,
					cwd=entry_name,
					url_home_xhr=url_for(func_name,action="xhr"),
					url_home=url_for(func_name),
					url_parent_dir_xhr=url_for(func_name,action="xhr",path=parent_directory_path),
					url_parent_dir=url_for(func_name,path=parent_directory_path),
					url_bookmark=url_for('bookmarks'),
					url_search=url_for(func_name,path=path,action="search"),
					browse_mode=True,
					atroot = atroot,
					func_name = func_name,
					root_display_name = display_name,
					on_file_click=bargate.lib.userdata.get_on_file_click(),
					no_items = no_items,
				)

			else:
				abort(400)

		elif request.method == 'POST':
			###############################
			# POST: UPLOAD
			###############################
			if action == 'jsonupload':
				ret = []

				uploaded_files = request.files.getlist("files[]")
			
				for ufile in uploaded_files:
			
					if bargate.lib.core.banned_file(ufile.filename):
						ret.append({'name' : ufile.filename, 'error': 'Filetype not allowed'})
						continue
					
					## Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
					filename = bargate.lib.core.secure_filename(ufile.filename)
					upload_path = full_path + '/' + filename

					## Check the new file name is valid
					try:
						bargate.lib.core.check_name(filename)
					except ValueError as e:
						ret.append({'name' : ufile.filename, 'error': 'Filename not allowed'})
						continue
					
					file_already_exists = False
					try:
						sfile = conn.getAttributes(share_name,upload_path)
						file_already_exists = True
					except OperationFailure as ex:
						pass
					except Exception as ex:
						ret.append({'name' : ufile.filename, 'error': 'Could not check if file already exists: ' + str(type(ex))})
						continue

					byterange_start = 0
					if 'Content-Range' in request.headers:
						byterange_start = int(request.headers['Content-Range'].split(' ')[1].split('-')[0])
						app.logger.debug("Chunked file upload request: Content-Range sent with byte range start of " + str(byterange_start) + " with filename " + filename)

					# Check if we're writing from the start of the file
					if byterange_start == 0:
						## We're truncating an existing file, or creating a new file
						## If the file already exists, check to see if we should overwrite
						if file_already_exists:
							if not bargate.lib.userdata.get_overwrite_on_upload():
								ret.append({'name' : ufile.filename, 'error': 'File already exists. You can enable overwriting files in Settings.'})
								continue

							## Now ensure we're not trying to upload a file on top of a directory (can't do that!)
							if sfile.isDirectory:
								ret.append({'name' : ufile.filename, 'error': "That name already exists and is a directory"})
								continue

					# Upload
					try:
						if byterange_start == 0:
							conn.storeFile(share_name,upload_path, ufile, timeout=120)
						else:
							conn.storeFileFromOffset(share_name,upload_path, ufile, offset=byterange_start)

						ret.append({'name' : ufile.filename})
					except Exception as ex:
						app.logger.debug("Exception when uploading a file: " + str(type(ex)) + ": " + str(ex) + traceback.format_exc())
						## TODO... need better error handling here, but it means delving through OperationFailure error codes :(
						ret.append({'name' : ufile.filename, 'error': 'Could not upload file: ' + str(type(ex))})
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
					bargate.lib.core.check_name(new_name)
				except ValueError as e:
					return jsonify({'code': 1, 'msg': 'The new name is invalid'})

				## Build paths
				old_path = full_path + "/" + old_name
				new_path = full_path + "/" + new_name

				app.logger.debug("asked to rename from " + old_path + " to " + new_path)

				## Check existing file/directory exists
				try:
					sfile = conn.getAttributes(share_name,old_path)
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Unable to read the existing entry'})

				if sfile.isDirectory:
					typestr = "directory"
				else:
					typestr = "file"

				try:
					conn.rename(share_name,old_path,new_path)
				except Exception as ex:
					app.logger.debug(ex)
					return jsonify({'code': 1, 'msg': 'Unable to rename: ' + str(type(ex))})
				else:
					app.logger.debug("Renamed from " + old_path + " to " + new_path)
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
					bargate.lib.core.check_name(dest)
				except ValueError as e:
					return jsonify({'code': 1, 'msg': 'The new name is invalid'})

				## Build paths
				src_path  = full_path + "/" + src
				dest_path = full_path + "/" + dest

				app.logger.debug("asked to copy from " + src + " to " + dest)

				## Check if existing file exists
				try:
					sfile = conn.getAttributes(share_name,src_path)
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'The file you tried to copy does not exist'})

				if sfile.isDirectory:
					return jsonify({'code': 1, 'msg': 'Unable to copy a directory!'})

				## Make sure the new file does not exist
				try:
					sfile = conn.getAttributes(share_name,dest_path)
					return jsonify({'code': 1, 'msg': 'The destination filename already exists'})
				except:
					# could not get attributes, so file does not exist, so lets continue
					pass

				# read into a local temp file, because you can't 'open' a file handle
				# in pysmb, you have to read the entire thing and store it somewhere
				# oh and we need to reset the file pos 'cos storeFile expects that
				try:
					tfile = tempfile.SpooledTemporaryFile(max_size=1048576)
					conn.retrieveFile(share_name, src_path, tfile)
					tfile.seek(0)
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'Could not read from the source file'})

				try:
					conn.storeFile(share_name, dest_path, tfile, timeout=120)
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
					bargate.lib.core.check_name(dirname)
				except ValueError as e:
					return jsonify({'code': 1, 'msg': 'That directory name is invalid'})

				dirname_path  = full_path + "/" + dirname

				try:
					conn.createDirectory(share_name,dirname_path)
				except Exception as ex:
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

				delete_path  = full_path + "/" + delete_name

				try:
					sfile = conn.getAttributes(share_name,delete_path)
				except Exception as ex:
					return jsonify({'code': 1, 'msg': 'The file server returned an error when asked to check the file to be deleted'})

				if sfile.isDirectory:
					try:
						conn.deleteDirectory(share_name, delete_path)
					except Exception as ex:
						return jsonify({'code': 1, 'msg': 'The file server returned an error when asked to delete the directory'})

					return jsonify({'code': 0, 'msg': "The directory '" + delete_name + "' was deleted"})

				else:
					try:
						conn.deleteFiles(share_name, delete_path)
					except Exception as ex:
						return jsonify({'code': 1, 'msg': 'The file server returned an error when asked to delete the file'})

					return jsonify({'code': 0, 'msg': "The file '" + delete_name + "' was deleted"})

			else:
				return jsonify({'code': 1, 'msg': "An invalid action was specified"})

	############################################################################

################################################################################

	def _init_search(self,libsmbclient,func_name,path,path_as_str,srv_path_as_str,uri_as_str,query):
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
			directory_entries = self.libsmbclient.opendir(uri_as_str).getdents()
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
				#entry = bargate.lib.smb.processDentry(entry, self.libsmbclient, self.func_name)
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


################################################################################

	def _sfile_load(self,sfile,srv_path, path, func_name):
		"""Takes a smb SharedFile object and returns a dictionary with information
		about that SharedFile object. 
		"""

		entry = {'skip': False, 'name': sfile.filename, 'size': sfile.file_size }

		## Skip entries for 'this dir' and 'parent dir'
		if entry['name'] == '.':
			entry['skip'] = True
		if entry['name'] == '..':
			entry['skip'] = True

		## Build the path
		if len(path) == 0:
			entry['path'] = entry['name']
		else:
			entry['path'] = path + '/' + entry['name']

		## Hide hidden files if the user has selected to do so (the default)
		if not bargate.lib.userdata.get_show_hidden_files():
			## UNIX hidden files
			if entry['name'].startswith('.'):
				entry['skip'] = True

			## Office temporary files
			if entry['name'].startswith('~$'):
				entry['skip'] = True

			## Other horrible Windows files
			hidden_entries = ['desktop.ini', '$RECYCLE.BIN', 'RECYCLER', 'Thumbs.db']

			if entry['name'] in hidden_entries:
				entry['skip'] = True

		if entry['skip']:
			return entry

		# Directories
		if sfile.isDirectory:
			entry['type'] = 'dir'
			entry['icon'] = 'fa fa-fw fa-folder'
			entry['stat'] = url_for(func_name,path=entry['path'],action='stat')
			entry['url']  = url_for(func_name,path=entry['path'])
			entry['jurl'] = url_for(func_name,action="xhr",path=entry['path'])

		# Files
		else:
			entry['type'] = 'file'

			## Generate 'mtype', 'mtype_raw' and 'icon'
			entry['icon'] = 'fa fa-fw fa-file-text-o'
			(entry['mtype'],entry['mtype_raw']) = bargate.lib.mime.filename_to_mimetype(entry['name'])
			entry['icon'] = bargate.lib.mime.mimetype_to_icon(entry['mtype_raw'])

			## Generate URLs to this file
			entry['stat']         = url_for(func_name,path=entry['path'],action='stat')
			entry['download']     = url_for(func_name,path=entry['path'],action='download')
			entry['open']         = entry['download']

			# modification time (last write)
			entry['mtime_raw'] = sfile.last_write_time
			entry['mtime']     = bargate.lib.core.ut_to_string(sfile.last_write_time)

			## Image previews
			if app.config['IMAGE_PREVIEW'] and entry['mtype_raw'] in bargate.lib.mime.pillow_supported:
				if int(entry['size']) <= app.config['IMAGE_PREVIEW_MAX_SIZE']:
					entry['img_preview'] = url_for(func_name,path=entry['path'],action='preview')

			## View-in-browser download type
			if bargate.lib.mime.view_in_browser(entry['mtype_raw']):
				entry['view'] = url_for(func_name,path=entry['path'],action='view')
				entry['open'] = entry['view']
	
		return entry

