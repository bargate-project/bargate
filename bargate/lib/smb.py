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
import bargate.lib.core
import bargate.lib.errors
import bargate.lib.userdata
import bargate.lib.mime
from bargate.lib.search import RecursiveSearchEngine
import string, os, io, smbc, sys, stat, pprint, urllib, re
from flask import Flask, send_file, request, session, g, redirect, url_for, abort, flash, make_response, jsonify, render_template

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

## from libsmbclient source
#00088 #define SMBC_WORKGROUP      1
#00089 #define SMBC_SERVER         2
#00090 #define SMBC_FILE_SHARE     3
#00091 #define SMBC_PRINTER_SHARE  4
#00092 #define SMBC_COMMS_SHARE    5
#00093 #define SMBC_IPC_SHARE      6
#00094 #define SMBC_DIR            7
#00095 #define SMBC_FILE           8
#00096 #define SMBC_LINK           9

################################################################################
################################################################################
################################################################################

def check_name(name):
	"""This function checks for invalid characters in a folder or file name or similar
	strings. It checks for a range of characters and invalid conditions as defined 
	by Microsoft here: http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx
	Raises an exception of ValueError if any failure condition is met by the string.
	"""
		
	## File names MUST NOT end in a space or a period (full stop)
	if name.endswith(' ') or name.endswith('.'):
		raise ValueError('File and folder names must not end in a space or period (full stop) character')
		
	## Run the file/folder name check through the generic path checker
	bargate.lib.smb.check_path(name)
	
	## banned characters which CIFS servers reject!
	invalidchars = re.compile(r'[<>/\\\":\|\?\*\x00]');
	
	## Check for the chars
	if invalidchars.search(name):
		raise ValueError('Invalid characters found. You cannot use the following characters in file or folder names: < > \ / : " ? *')
		
	return name
		
################################################################################
################################################################################
################################################################################

def check_path(path):
	"""This function checks for invalid characters in an entire path. It checks to ensure
	that paths don't contain strings which manipulate the path e.g up path or similar.
	Raises an exception of ValueError if any failure condition is met by the string.
	"""
	
	if path.startswith(".."):
		raise ValueError('Invalid path. Paths cannot start with ".."')

	if path.startswith("./"):
		raise ValueError('Invalid path. Paths cannot start with "./"')

	if path.startswith(".\\"):
		raise ValueError('Invalid path. Paths cannot start with ".\"')

	if '/../' in path:
		raise ValueError('Invalid path. Paths cannot contain "/../"')

	if '\\..\\' in path:
		raise ValueError('Invalid path. Paths cannot contain "\..\"')

	if '\\.\\' in path:
		raise ValueError('Invalid path. Paths cannot contain "\.\"')

	if '/./' in path:
		raise ValueError('Invalid path. Paths cannot contain "/./"')
		
	return path
	
################################################################################
################################################################################
################################################################################

def wb_sid_to_name(sid):
	import subprocess
	process = subprocess.Popen([app.config['WBINFO_BINARY'], '--sid-to-name',sid], stdout=subprocess.PIPE)
	sout, serr = process.communicate()
	sout = sout.rstrip()

	if sout.endswith(' 1') or sout.endswith(' 2'):
		return sout[:-2]
	else:
		return sout

################################################################################
################################################################################
################################################################################

def statEntry(libsmbclient,url):
	"""Run stat() on a URI and return a dictionary with friendly named keys"""

	# Strip off trailing slashes as they're useless to us
	if url.endswith('/'):
		url = url[:-1]

	fstat = libsmbclient.stat(url)

	return {'mode': fstat[0], 	## unix mode
			'ino': fstat[1], 	## inode number
			'dev': fstat[2], 	## device number
			'nlink': fstat[3],	## number of links
			'uid': fstat[4], 	## user ID
			'gid': fstat[5], 	## group ID
			'size': fstat[6], 	## size in bytes
			'atime': fstat[7],	## access time
			'mtime': fstat[8],	## modify time
			'ctime': fstat[9]	## change time
			}

################################################################################
################################################################################
################################################################################

def getEntryType(libsmbclient,uri):
	## stat the file, st_mode has all the info we need

	## Strip off trailing slashes as they're useless to us
	if uri.endswith('/'):
		uri = uri[:-1]

	## stat the URI
	try:
		fstat = libsmbclient.stat(uri)
	except Exception as ex:
		return bargate.lib.errors.smbc_handler(ex,uri)

	return statToType(fstat)
	
################################################################################
################################################################################
################################################################################

def statToType(fstat):

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
################################################################################
################################################################################

def loadDentry(dentry,srv_path_as_str, path, path_as_str):
	"""This function takes a directory entry returned from getdents and returns
		a dictionary of information about the dentry. Its primary purpose is
		to return unicode and str objects for the name, path and URI of the entry
		and determine if the entry should be 'skipped'.

		'skip' means the file should be omitted from results because either 
		it is '.' or '..' or is considered a 'hidden' file.

		The dictionary returned contains the following keys:

			- type			Either 'file', 'dir', 'share' or 'other'
			- name			The entry name as a unicode object
			- name_as_str	The entry name as a str object
			- uri			
			- uri_as_str	The full URI including smb:// to the entry as a str object
			- path			The full path (not including smb:// and  the server name) to the entry as a unicode object
			- skip			Should this entry be shown to the user or not
		"""

	entry = {'skip': False, 'name': dentry.name}

	## In earlier versions of pysmbc getdents returns regular python str objects
	## and not unicode, so we have to convert to unicode via .decode. However, from
	## 1.0.15.1 onwards pysmbc returns unicode (i.e. its probably doing a .decode for us)
	## so we need to check what we get back and act correctly based on that.
	## urllib needs str objects, not unicode objects, so we also have to maintain
	## a copy of a str object *and* a unicode object. I believe that adding Python 3
	## support is why 1.0.15.1 onwards returns unicode objects instead of str.

	if isinstance(entry['name'], str):
		## store str object
		entry['name_as_str'] = entry['name']
		## create unicode object
		entry['name'] = entry['name'].decode("utf-8")
	else:
		## create str object
		entry['name_as_str'] = entry['name'].encode("utf-8")

	## Skip entries for 'this dir' and 'parent dir'
	if entry['name'] == '.':
		entry['skip'] = True
	if entry['name'] == '..':
		entry['skip'] = True

	## Build the entire URI (str object)
	entry['uri_as_str'] = srv_path_as_str + path_as_str + '/' + urllib.quote(entry['name_as_str'])

	## Build the path (unicode object)
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

	if dentry.smbc_type == bargate.lib.smb.SMB_FILE:
		entry['type'] = 'file'

	elif dentry.smbc_type == bargate.lib.smb.SMB_DIR:
		entry['type'] = 'dir'


	elif dentry.smbc_type == bargate.lib.smb.SMB_SHARE:
		entry['type'] = 'share'

		## check last char for $ ('administrative' shares)
		if entry['name'].endswith == "$":
			entry['skip'] = True
	else:
		entry['type'] = 'other'
		entry['skip'] = True

	return entry

################################################################################
################################################################################
################################################################################

def processDentry(entry,libsmbclient,func_name):
	"""This function takes a directory entry returned from the loadDentry
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
		entry['open']         = entry['download']

		try:

			## For files we stat the file and look up a bunch of stuff
			fstat = statEntry(libsmbclient,entry['uri_as_str'])
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
			entry['open'] = entry['view']

	elif entry['type'] == 'dir':
		## Set the icon for directories
		entry['icon'] = 'fa fa-fw fa-folder'

		## Generate URLs to this directory
		entry['stat'] = url_for(func_name,path=entry['path'],action='stat')
		entry['open'] = url_for(func_name,path=entry['path'])

	elif entry['type'] == 'share':
		## Set the icon for shares
		entry['icon'] = 'fa fa-fw fa-archive'

		## Generate a URL for this share
		entry['open'] = url_for(func_name,path=entry['path'])

	elif entry['type'] == 'other':
		entry['icon'] = 'fa fa-question-circle'

	return entry
	
################################################################################
################################################################################
################################################################################

## 'path' is always unicode
## 'uri' is always unicode
## 'path_as_str' is a str object version of path
## 'uri_as_str' is a str object version of uri
## uri, or rather uri_as_str, is used when making calls to pysmbc
## path is used when generating data to send to jinja
## path_as_str is used when building a uri_as_str
def connection(srv_path,func_name,active=None,display_name="Home",action='browse',path=''):

	## ensure srv_path (the server URI and share) ends with a trailing slash
	if not srv_path.endswith('/'):
		srv_path = srv_path + '/'

	## srv_path should always start with smb://, we don't support anything else.
	if not srv_path.startswith("smb://"):
		return bargate.lib.errors.stderr("Invalid server path","The server URL must start with smb://")

	## We need a non-unicode srv_path for pysmbc calls
	srv_path_as_str = srv_path.encode('utf-8')

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

	## Prepare to talk to the file server
	libsmbclient = smbc.Context(auth_fn=bargate.lib.user.get_smbc_auth)

	############################################################################
	## HTTP GET ACTIONS ########################################################
	# actions: download/view, browse, stat
	############################################################################

	if request.method == 'GET':
		## pysmbc needs urllib quoted str objects (not unicode objects)
		path_as_str = urllib.quote(path.encode('utf-8'))
				
		## Check the path is valid
		try:
			bargate.lib.smb.check_path(path)
		except ValueError as e:
			return bargate.lib.errors.invalid_path()

		## Build the URI
		uri        = srv_path + path
		uri_as_str = srv_path_as_str + path_as_str

		## Log this activity
		app.logger.info('User "' + session['username'] + '" connected to "' + srv_path + '" using endpoint "' + func_name + '" and action "' + action + '" using GET and path "' + path + '" from "' + request.remote_addr + '" using ' + request.user_agent.string)

		## Work out if there is a parent directory
		## and work out the entry name (filename or directory name being browsed)
		if len(path) > 0:
			(parent_directory_path,seperator,entryname) = path.rpartition('/')
			## if seperator was not found then the first two strings returned will be empty strings
			if len(parent_directory_path) > 0:
				parent_directory = True

				parent_directory_path_as_str = urllib.quote(parent_directory_path.encode('utf-8'))

				## update the parent redirect with the correct path
				parent_redirect = redirect(url_for(func_name,path=parent_directory_path))
				error_redirect  = parent_redirect

			else:
				parent_directory = False

		else:
			parent_directory = False
			parent_directory_path = ""
			parent_directory_path_as_str = ""
			entryname = ""

		## parent_directory is either True/False if there is one
		## entryname will either be the part after the last / or the full path
		## parent_directory_path will be empty string or the parent directory path

################################################################################
# DOWNLOAD OR 'VIEW' FILE
################################################################################

		if action == 'download' or action == 'view':

			try:
				fstat    = libsmbclient.stat(uri_as_str)
			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri_as_str,error_redirect)

			## ensure item is a file
			if not bargate.lib.smb.statToType(fstat) == SMB_FILE:
				return bargate.lib.errors.invalid_item_download(error_redirect)

			try:
				file_object = libsmbclient.open(uri_as_str)

				## Default to sending files as an 'attachment' ("Content-Disposition: attachment")
				attach = True

				## Guess the mime type  based on file extension
				(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entryname)

				## If the user requested to 'view' (don't download as an attachment) make sure we allow it for that filetype
				if action == 'view':
					if bargate.lib.mime.view_in_browser(mtype):
						attach = False

				## Send the file to the user
				resp = make_response(send_file(file_object,add_etags=False,as_attachment=attach,attachment_filename=entryname,mimetype=mtype))
				resp.headers['content-length'] = str(fstat[6])
				return resp
	
			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri_as_str,error_redirect)

################################################################################
# IMAGE PREVIEW
################################################################################
		
		elif action == 'preview':
			if not app.config['IMAGE_PREVIEW']:
				abort(400)

			try:
				fstat = libsmbclient.stat(uri_as_str)
			except Exception as ex:
				abort(400)

			## ensure item is a file
			if not bargate.lib.smb.statToType(fstat) == SMB_FILE:
				abort(400)
				
			## guess a mimetype
			(ftype,mtype) = bargate.lib.mime.filename_to_mimetype(entryname)
			
			## Check size is not too large for a preview
			if fstat[6] > app.config['IMAGE_PREVIEW_MAX_SIZE']:
				abort(403)

			## Only preview files that Pillow supports
			if not mtype in bargate.lib.mime.pillow_supported:
				abort(400)

			## Open the file
			try:
				file_object = libsmbclient.open(uri_as_str)
			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri_as_str,error_redirect)
			
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
				fstat = libsmbclient.stat(uri_as_str)
			except Exception as ex:
				return jsonify({'error': 1, 'reason': 'An error occured: ' + str(type(ex)) + ": " + str(ex)})

			data = {}	
			data['filename']              = entryname
			data['size']                  = fstat[6]
			data['atime']                 = bargate.lib.core.ut_to_string(fstat[7])
			data['mtime']                 = bargate.lib.core.ut_to_string(fstat[8])
			(data['ftype'],data['mtype']) = bargate.lib.mime.filename_to_mimetype(data['filename'])
			
			if app.config['WBINFO_LOOKUP']:
				try:
					data['owner'] = bargate.lib.smb.wb_sid_to_name(libsmbclient.getxattr(uri_as_str,smbc.XATTR_OWNER))
					data['group'] = bargate.lib.smb.wb_sid_to_name(libsmbclient.getxattr(uri_as_str,smbc.XATTR_GROUP))
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

			searchEngine = RecursiveSearchEngine(libsmbclient,func_name,path,path_as_str,srv_path_as_str,uri_as_str,query)
			results, timeout_reached = searchEngine.search()

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
			
################################################################################
# BROWSE / DIRECTORY / LIST FILES
################################################################################
		
		elif action == 'browse':		

			## Try getting directory contents
			try:
				directory_entries = libsmbclient.opendir(uri_as_str).getdents()
			except smbc.NotDirectoryError as ex:
				## If there is a parent directory, go up to it
				if parent_directory:
					return url_for(func_name,path=parent_directory_path)
				else:
					return bargate.lib.errors.stderr("Bargate is misconfigured","The path given for the share " + func_name + " is not a directory!")

			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)

			## Seperate out dirs and files into two lists
			dirs  = []
			files = []

			for dentry in directory_entries:
				# Create a new dict for the entry
				entry = loadDentry(dentry, srv_path_as_str, path, path_as_str)

				# Continue to next entry if we found it should be skipped
				if entry['skip']:
					continue
				else:
					# Further process the entry (stat it, load the icon, etc)
					entry = processDentry(entry,libsmbclient,func_name)

				if entry['type'] == 'file':
					files.append(entry)
				elif entry['type'] == 'dir' or entry['type'] == 'share':
					dirs.append(entry)

			## Build a breadcrumbs trail ##
			crumbs = []
			parts  = path.split('/')
			b4     = ''

			## Build up a list of dicts, each dict representing a crumb
			for crumb in parts:
				if len(crumb) > 0:
					crumbs.append({'name': crumb, 'url': url_for(func_name,path=b4+crumb)})
					b4 = b4 + crumb + '/'

			## Are we at the root?
			if len(path) == 0:
				atroot = True
			else:
				atroot = False
				
			## are there any items?
			no_items = False
			if len(files) == 0 and len(dirs) == 0:
				no_items = True

			## What layout does the user want?
			layout = bargate.lib.userdata.get_layout()

			## Render the template
			return render_template('directory-' + layout + '.html',
				active=active,
				dirs=dirs,
				files=files,
				crumbs=crumbs,
				path=path,
				cwd=entryname,
				url_home=url_for(func_name),
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
		action = request.form['action']
		path   = request.form['path']
		
		## Check the path is valid
		try:
			bargate.lib.smb.check_path(path)
		except ValueError as e:
			return bargate.lib.errors.invalid_path()

		## pysmbc needs urllib quoted str objects, not unicode objects
		path_as_str = urllib.quote(path.encode('utf-8'))

		## Build the URI
		uri        = srv_path + path
		uri_as_str = srv_path_as_str + path_as_str

		## Log this activity
		app.logger.info('User "' + session['username'] + '" connected to "' + srv_path + '" using func name "' + func_name + '" and action "' + action + '" using POST and path "' + path + '" from "' + request.remote_addr + '" using ' + request.user_agent.string)


		## Work out if there is a parent directory
		## and work out the entry name (filename or directory name being browsed)
		if len(path) > 0:
			(parent_directory_path,seperator,entryname) = path.rpartition('/')
			## if seperator was not found then the first two strings returned will be empty strings
			if len(parent_directory_path) > 0:
				parent_directory = True
				parent_directory_path_as_str = urllib.quote(parent_directory_path.encode('utf-8'))
				parent_redirect = redirect(url_for(func_name,path=parent_directory_path))
				error_redirect = parent_redirect
			else:
				parent_directory = False

		else:
			parent_directory = False
			parent_directory_path = ""

		## parent_directory is either True/False if there is one
		## entryname will either be the part after the last / or the full path
		## parent_directory_path will be empty string or the parent directory path

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
				upload_uri_as_str = uri_as_str + '/' + urllib.quote(filename.encode('utf-8'))

				## Check the new file name is valid
				try:
					bargate.lib.smb.check_name(filename)
				except ValueError as e:
					ret.append({'name' : ufile.filename, 'error': 'Filename not allowed'})
					continue
					
				## Check to see if the file exists
				fstat = None
				try:
					fstat = libsmbclient.stat(upload_uri_as_str)
				except smbc.NoEntryError:
					app.logger.debug("Upload filename of " + upload_uri_as_str + " does not exist, ignoring")
					## It doesn't exist so lets continue to upload
				except Exception as ex:
					app.logger.error("Exception when uploading a file: " + str(type(ex)) + ": " + str(ex) + traceback.format_exc())
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
							itemType = bargate.lib.smb.getEntryType(libsmbclient,upload_uri_as_str)
							if itemType == bargate.lib.smb.SMB_DIR:
								ret.append({'name' : ufile.filename, 'error': "That name already exists and is a directory"})
								continue

						## Open the file for the first time, truncating or creating it if necessary
						app.logger.debug("Opening for writing with O_CREAT and TRUNC")
						wfile = libsmbclient.open(upload_uri_as_str,os.O_CREAT | os.O_TRUNC | os.O_WRONLY)
					else:
						## Open the file and seek to where we are going to write the additional data
						app.logger.debug("Opening for writing with O_WRONLY")
						wfile = libsmbclient.open(upload_uri_as_str,os.O_WRONLY)
						wfile.seek(byterange_start)

					while True:
						buff = ufile.read(io.DEFAULT_BUFFER_SIZE)
						if not buff:
							break
						wfile.write(buff)

					wfile.close()
					ret.append({'name' : ufile.filename})

				except Exception as ex:
					app.logger.error("Exception when uploading a file: " + str(type(ex)) + ": " + str(ex) + traceback.format_exc())
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
				bargate.lib.smb.check_name(new_filename)
			except ValueError as e:
				return bargate.lib.errors.invalid_name()

			## build new URI
			new_filename_as_str = urllib.quote(new_filename.encode('utf-8'))
			if parent_directory:
				new_uri_as_str = srv_path_as_str + parent_directory_path_as_str + '/' + new_filename_as_str
			else:
				new_uri_as_str = srv_path_as_str + new_filename_as_str

			## get the item type of the existing 'filename'
			itemType = bargate.lib.smb.getEntryType(libsmbclient,uri_as_str)

			if itemType == bargate.lib.smb.SMB_FILE:
				typemsg = "The file"
			elif itemType == bargate.lib.smb.SMB_DIR:
				typemsg = "The directory"
			else:
				return bargate.lib.errors.invalid_item_type(error_redirect)

			try:
				libsmbclient.rename(uri_as_str,new_uri_as_str)
			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)
			else:
				flash(typemsg + " '" + entryname + "' was renamed to '" + request.form['newfilename'] + "' successfully.",'alert-success')
				return parent_redirect

################################################################################
# COPY FILE
################################################################################

		elif action == 'copy':

			try:
				## stat the source file first
				source_stat = libsmbclient.stat(uri_as_str)

				## size of source
				source_size = source_stat[6]

				## determine item type
				itemType = bargate.lib.smb.statToType(source_stat)

				## ensure item is a file
				if not itemType == SMB_FILE:
					return bargate.lib.errors.invalid_item_copy(error_redirect)

			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)

			## Get the new filename
			dest_filename = request.form['filename']
			
			## Check the new file name is valid
			try:
				bargate.lib.smb.check_name(request.form['filename'])
			except ValueError as e:
				return bargate.lib.errors.invalid_name(error_redirect)
			
			## encode the new filename and quote the new filename
			if parent_directory:
				dest = srv_path_as_str + parent_directory_path_as_str + '/' + urllib.quote(dest_filename.encode('utf-8'))
			else:
				dest = srv_path_as_str + urllib.quote(dest_filename.encode('utf-8'))

			## Make sure the dest file doesn't exist
			try:
				libsmbclient.stat(dest)
			except smbc.NoEntryError as ex:
				## This is what we want - i.e. no file/entry
				pass
			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)

			## Assuming we got here without an exception, open the source file
			try:		
				source_fh = libsmbclient.open(uri_as_str)
			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)

			## Assuming we got here without an exception, open the dest file
			try:		
				dest_fh = libsmbclient.open(dest, os.O_CREAT | os.O_WRONLY | os.O_TRUNC )

			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,srv_path + dest,error_redirect)

			## try reading then writing blocks of data, then redirect!
			try:
				location = 0
				while(location >= 0 and location < source_size):
					chunk = source_fh.read(1024)
					dest_fh.write(chunk)
					location = source_fh.seek(1024,location)

			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,srv_path + dest,error_redirect)

			flash('A copy of "' + entryname + '" was created as "' + dest_filename + '"','alert-success')
			return parent_redirect

################################################################################
# MAKE DIR
################################################################################

		elif action == 'mkdir':
			## Check the path is valid
			try:
				bargate.lib.smb.check_name(request.form['directory_name'])
			except ValueError as e:
				return bargate.lib.errors.invalid_name(error_redirect)

			mkdir_uri = uri_as_str + '/' + urllib.quote(request.form['directory_name'].encode('utf-8'))

			try:
				libsmbclient.mkdir(mkdir_uri,0755)
			except Exception as ex:
				return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)
			else:
				flash("The folder '" + request.form['directory_name'] + "' was created successfully.",'alert-success')
				return redirect(url_for(func_name,path=path))

################################################################################
# DELETE FILE
################################################################################

		elif action == 'unlink':
			uri = uri.encode('utf-8')

			## get the item type of the entry we've been asked to delete
			itemType = bargate.lib.smb.getEntryType(libsmbclient,uri_as_str)

			if itemType == bargate.lib.smb.SMB_FILE:
				try:
					libsmbclient.unlink(uri_as_str)
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)
				else:
					flash("The file '" + entryname + "' was deleted successfully.",'alert-success')
					return parent_redirect

			elif itemType == bargate.lib.smb.SMB_DIR:
				try:
					libsmbclient.rmdir(uri_as_str)
				except Exception as ex:
					return bargate.lib.errors.smbc_handler(ex,uri,error_redirect)
				else:
					flash("The directory '" + entryname + "' was deleted successfully.",'alert-success')
					return parent_redirect
			else:
				return bargate.lib.errors.invalid_item_type(error_redirect)

		else:
			abort(400)

################################################################################
