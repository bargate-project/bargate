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
import bargate.errors
import string, os, smbc, sys, stat, pprint, urllib, re
from flask import Flask, send_file, request, session, g, redirect, url_for, abort, flash, make_response, jsonify

### Python imaging stuff
from PIL import Image
import glob
import StringIO

## NOTE! pysmbc sucks for unicode. See:
## https://lists.fedorahosted.org/pipermail/system-config-printer-devel/2011-September/000108.html

#### SMB entry types
SMB_ERR   = -1
SMB_SHARE = 3
SMB_DIR   = 7
SMB_FILE  = 8
SMB_LINK  = 9

### stat response
# (33188, 18446744071764076844L, 1219393884L, 1L, 48, 48, 592517L, 1363042779, 1363042779, 1363042779)
# st_mode (unix mode)
# st_ino inode number
# st_dev device number
# st_nlink number of links
# uid
# gid
# size
# atime
# mtime
# ctime

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
	bargate.smb.check_path(name)
	
	## banned characters which CIFS servers reject!
	invalidchars = re.compile(r'[<>/\\\":\|\?\*\x00]');
	
	## Check for the chars
	if invalidchars.search(name):
		raise ValueError('Invalid characters found. You cannot use the following characters in file or folder names: < > \ / : " ? *')
		
	return name
		
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

def wb_sid_to_name(sid):
	import subprocess
	process = subprocess.Popen(['/usr/bin/wbinfo', '--sid-to-name',sid], stdout=subprocess.PIPE)
	sout, serr = process.communicate()
	
	sout = sout.rstrip()

	## TODO better error handling!!!
	
	if sout.endswith(' 1') or sout.endswith(' 2'):
		return sout[:-2]
	else:
		return sout

################################################################################

def statURI(ctx,uri):
	## stat the file
	## return a dictionary with friendly named access to data

	## Strip off trailing slashes as they're useless to us
	if uri.endswith('/'):
		uri = uri[:-1]

	## stat the URI
	try:
		fstat = ctx.stat(uri)
	except Exception as ex:
		return bargate.errors.smbc_handler(ex,uri)

	dstat = {}
	dstat['mode']  = fstat[0]
	dstat['ino']   = fstat[1]
	dstat['dev']   = fstat[2]
	dstat['nlink'] = fstat[3]	
	dstat['uid']   = fstat[4]
	dstat['gid']   = fstat[5]
	dstat['size']  = fstat[6]
	dstat['atime'] = fstat[7]
	dstat['mtime'] = fstat[8]
	dstat['ctime'] = fstat[9]

	return dstat

################################################################################

def getEntryType(ctx,uri):
	## stat the file, st_mode has all the info we need
	## thanks to clayton for fixing this problem

	## Strip off trailing slashes as they're useless to us
	if uri.endswith('/'):
		uri = uri[:-1]

	## stat the URI
	try:
		fstat = ctx.stat(uri)
	except Exception as ex:
		return bargate.errors.smbc_handler(ex,uri)

	return statToType(fstat)
	
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
#### SHARE HANDLER
		
@bargate.core.login_required
@bargate.core.downtime_check
def share_handler(path):
	## Get the path variable
	svrpath = app.sharesConfig.get(request.endpoint,'path')

	## Variable substition for username
	svrpath = svrpath.replace("%USERNAME%",session['username'])
	svrpath = svrpath.replace("%USER%",session['username'])

	## LDAP home dir substitution support
	if app.config['LDAP_HOMEDIR']:
		if 'ldap_homedir' in session:
			if not session['ldap_homedir'] == None:
				svrpath = svrpath.replace("%LDAP_HOMEDIR%",session['ldap_homedir'])

	## Get the display name
	display = app.sharesConfig.get(request.endpoint,'display')

	## What menu is active?
	menu = app.sharesConfig.get(request.endpoint,'menu')

	## Run the page!
	return bargate.smb.connection(svrpath,request.endpoint,menu,display,path)
		
################################################################################

def connection(srv_path,func_name,active=None,display_name="Home",path=''):
	## ensure srv_path ends with a trailing slash
	if not srv_path.endswith('/'):
		srv_path = srv_path + '/'
	
	if active == None:
		active = func_name

	## Load the SMB engine
	ctx = smbc.Context(auth_fn=bargate.core.get_smbc_auth)

	############################################################################
	## HTTP GET ACTIONS ########################################################
	# actions: download, browse, view
	############################################################################

	if request.method == 'GET':
		## pysmbc needs urllib quoted strings, but urllib can't handle unicode
		## so convert to str via 'encode utf8' and then urllib quote
		## it seems pysmbc can't handle unicode strings either anyway
		Spath = path.encode('utf8')
		Qpath = urllib.quote(Spath)
				
		## Check the path is valid
		try:
			bargate.smb.check_path(path)
		except ValueError as e:
			return bargate.errors.output_error('Invalid path',str(e))

		## Build the URI
		# uri is not str, its unicode, so uri must not be given to pysmbc/urllib
		uri = srv_path + path
		# uri_as_str CAN be given to pysmbc/urllib as its a byte string or 'str' in python land
		uri_as_str = srv_path.encode('utf8') + Qpath
		
		## Determine the action type
		action = request.args.get('action','browse')

		## Debug this in logs
		app.logger.info('User "' + session['username'] + '" connected to "' + srv_path + '" using endpoint "' + func_name + '" and action "' + action + '" using GET and path "' + path + '" from "' + request.remote_addr + '" using ' + request.user_agent.string)

################################################################################
# DOWNLOAD FILE
################################################################################

		if action == 'download':

			## Pull the filename out of the path
			(before,sep,after) = path.rpartition('/')
			if len(sep) > 0:
				filename = after
				error_redirect = redirect(url_for(func_name,path=before))
			else:
				filename = path
				error_redirect = redirect(url_for(func_name))

			## Filename now has to be encoded
			## We can do this before the above rpartition cos the quoting will remove / chars
			filename = filename.encode('utf8')

			try:
				## stat the file first
				fstat = ctx.stat(uri_as_str)

				## determine item type
				itemType = bargate.smb.statToType(fstat)

				## ensure item is a file
				if not itemType == SMB_FILE:
					return bargate.errors.invalid_item_download(error_redirect)

			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri_as_str,error_redirect)

			try:		
				## Assuming we got here without an exception, open the file
				cfile = ctx.open(uri_as_str)

				## don't set as attachment for certain file types!
				attach = True

				## Check to see if the user wants a in-browser view
				inbrowser = request.args.get('inbrowser',False)

				## If the user requested in-browser view (rather than download), make sure we allow it for that filetype
				if inbrowser:
					(ftype,mtype) = bargate.mime.filename_to_mimetype(filename)
					if bargate.mime.view_in_browser(mtype):
						attach = False

				## TODO BUG HERE WITH web browsers without PDF viewers.
				## if you set attach = False, then the filename is not sent correctly...
				## see the mime module for more

				## Download the file

				resp = make_response(send_file(cfile,add_etags=False,as_attachment=attach,attachment_filename=filename))
				resp.headers['content-length'] = str(fstat[6])
				return resp
	
			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri_as_str,error_redirect)

################################################################################
# IMAGE PREVIEW
################################################################################
		
		elif action == 'preview':
			try:
				fstat = ctx.stat(uri_as_str)
			except Exception as ex:
				abort(400)

			stat_type = statToType(fstat)
			if not stat_type == SMB_FILE:
				abort(400)
				
			## Pull the filename out of the path
			(before,sep,after) = path.rpartition('/')
			if len(sep) > 0:
				filename = after

				## Build a breadcrumbs trail ##
				crumbs = []
				parts = before.split('/')
				b4 = ''

				## Build up a list of dicts, each dict representing a crumb
				for crumb in parts:
					if len(crumb) > 0:
						crumbs.append({'name': crumb, 'url': url_for(func_name,path=b4+crumb)})
						b4 = b4 + crumb + '/'

			else:
				filename = path
				crumbs = []
				
			## guess a mimetype
			(ftype,mtype) = bargate.mime.filename_to_mimetype(filename)
			
			if fstat[6] > 10485760:
				abort(403)

			if not mtype.startswith('image'):
				abort(400)
				
			cfile = ctx.open(uri_as_str)
			
			## Read the file into memory first, because the PIL library sucks ass and tries random shit like readline()
			## which it claims it won't try, but...does anyway. Pysmbc's File object doesnt, shockingly, have a readline()
			sfile = StringIO.StringIO(cfile.read())
			pil_img = Image.open(sfile).convert('RGB')
			size = 200, 200
			pil_img.thumbnail(size, Image.ANTIALIAS)

			img_io = StringIO.StringIO()
			pil_img.save(img_io, 'JPEG', quality=85)
			img_io.seek(0)
			return send_file(img_io, mimetype='image/jpeg')

################################################################################
# VIEW FILE PROPERTIES
################################################################################
			
		elif action == 'view':
			## Build the URL to the parent directory (for errors, and for the template output)
			if len(path) > 0:
				(before,sep,after) = path.rpartition('/')
				if len(sep) > 0:
					url_parent_dir = url_for(func_name,path=before)
				else:
					url_parent_dir = url_for(func_name)
			else:
				## Then we must be at the root, which is a dir. Go away.
				return redirect(url_for(func_name))
				
			## try to stat the file
			try:
				fstat = ctx.stat(uri_as_str)
			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri,redirect(url_parent_dir))

			## Ensure we stat'ed a file and not a directory
			stat_type = statToType(fstat)
			if not stat_type == SMB_FILE:
				flash("Sorry, you can only the view the properties of files!",'alert-danger')
				return redirect(url_parent_dir)
	
			## Pull the filename out of the path
			(before,sep,after) = path.rpartition('/')
			if len(sep) > 0:
				filename = after

				## Build a breadcrumbs trail ##
				crumbs = []
				parts = before.split('/')
				b4 = ''

				## Build up a list of dicts, each dict representing a crumb
				for crumb in parts:
					if len(crumb) > 0:
						crumbs.append({'name': crumb, 'url': url_for(func_name,path=b4+crumb)})
						b4 = b4 + crumb + '/'

			else:
				filename = path
				crumbs = []
				
			try:
				if app.debug:
					flash("debug: " + ctx.getxattr(uri_as_str,smbc.XATTR_ALL),'alert-danger')
                                
				net_sec_desc_owner = bargate.smb.wb_sid_to_name(ctx.getxattr(uri_as_str,smbc.XATTR_OWNER))
				net_sec_desc_group = bargate.smb.wb_sid_to_name(ctx.getxattr(uri_as_str,smbc.XATTR_GROUP))

			except Exception as ex:
				## If we're in debug mode then print the error
				if app.debug:
					net_sec_desc_owner = "Error reading attributes: " + str(ex)	
					net_sec_desc_group = "Error reading attributes: " + str(ex)
	
				## In normal usage, just set user and group to unknown if we get an exception
				else:
					net_sec_desc_owner = "Unknown"
					net_sec_desc_group = "Unknown"
				
			## URLs
			url_home=url_for(func_name)
			url_download = url_for(func_name,path=path,action='download')
			url_view = url_for(func_name,path=path,action='view')
			url_rename = url_for(func_name,action='rename')

			## stat translation into useful stuff
			stat_atime = bargate.core.ut_to_string(fstat[7])
			stat_mtime = bargate.core.ut_to_string(fstat[8])
			stat_ctime = bargate.core.ut_to_string(fstat[9])

			## guess a mimetype
			(ftype,mtype) = bargate.mime.filename_to_mimetype(filename)

			## pick a representative file icon
			ficon = bargate.mime.mimetype_to_icon(mtype)

			## file size
			fsize = bargate.core.str_size(fstat[6])

			## View-in-browser download type
			if bargate.mime.view_in_browser(mtype):
				url_bdownload = url_for(func_name,path=path,action='download',inbrowser='True')
			else:
				url_bdownload = None

			## Render the template
			return bargate.core.render_page('view.html', active=active,
				crumbs=crumbs,
				path=path,
				url_home=url_home,
				url_parent_dir=url_parent_dir,
				url_download=url_download,
				url_bdownload=url_bdownload,
				url_view=url_view,
				url_rename=url_rename,
				filename=filename,
				stat=fstat,
				atime=stat_atime,
				mtime=stat_mtime,
				ctime=stat_ctime,
				mtype = mtype,
				ftype = ftype,
				ficon = ficon,
				fsize = fsize,
				root_display_name = display_name,
				net_sec_desc_owner = net_sec_desc_owner,
				net_sec_desc_group = net_sec_desc_group,
			)

################################################################################
# BROWSE / DIRECTORY / LIST FILES
################################################################################
		
		elif action == 'browse':		
			## Try getting directory contents
			try:
				dentries = ctx.opendir (uri_as_str).getdents ()
			except Exception as ex:
				# Place to redirect to, if any
				redir = None

				# Path has been set, so we might be able to get to a parent dir,
				# which lets us set a redirect path for the error.
				if len(path) > 0:
					(before,sep,after) = path.rpartition('/')
					if len(sep) > 0:
						redir = redirect(url_for(func_name,path=before))
					else:
						redir = redirect(url_for(func_name))

				return bargate.errors.smbc_handler(ex,uri,redir)

			## Seperate out dirs and files into two arrays
			dirs = []
			files = []

			## List each entry and build up a list of dictionarys
			for dentry in dentries:
				# Create a new dict for the entry
				entry = {}

				# Set a default icon and set name
				entry['icon'] = 'fa fa-fw fa-file-text-o'
				entry['name'] = dentry.name

				## Skip . and ..
				if entry['name'] == '.':
					continue
				if entry['name'] == '..':
					continue


				## In earlier versions of pysmbc getdents returns regular python str objects
				## and not unicode, so we have to convert to unicode via .decode. However, from
				## 1.0.15.1 onwards pysmbc returns unicode (i.e. its probably doing a .decode for us)
				## so we need to check what we get back and act correctly based on that.
				## SADLY! urllib2 needs str objects, not unicode objects, so we also have to maintain
				## a copy of a str object *and* a unicode object.

				if isinstance(entry['name'], str):
					## str object
					entry['name_as_str'] = entry['name']
					## unicode object
					entry['name'] = entry['name'].decode("utf-8")
				else:
					## str object
					entry['name_as_str'] = entry['name'].encode("utf-8")

				## Create a REGULAR str urllib quoted string for use to send back to ctx calls (only in python)
				## path is UNICODE. urllib needs string. Use Spath and Sname.
				entry['uri_as_str'] = srv_path + urllib.quote(Spath) + '/' + urllib.quote(entry['name_as_str'])

				## Add the URI (the full path) as an element to the entry dict
				if len(path) == 0:
					entry['path'] = entry['name']
				else:
					entry['path'] = path + '/' + entry['name']

				## Hide hidden files if the user has selected to do so (the default)
				if not bargate.settings.show_hidden_files():
					## check first character for . (unix hidden)
					if entry['name'][0] == ".":
						continue

					## hide typical windows hidden files
					if entry['name'] == 'desktop.ini': continue  # desktop settings
					if entry['name'] == '$RECYCLE.BIN': continue # recycle bin (vista/7)
					if entry['name'] == 'RECYCLER': continue     # recycle bin (xp)
					if entry['name'] == 'Thumbs.db': continue    # windows pic/video thumbnails
					if entry['name'] == 'public_html': continue  # old public_html directories
					if entry['name'].startswith('~$'): continue  # temp files (office)

				## FILE ########################################################
				if dentry.smbc_type == bargate.smb.SMB_FILE:

					## Entry type
					entry['type'] = 'file'

					## Stat the file so we get file size and other bits. 
					dstat = statURI(ctx,entry['uri_as_str'])

					if 'mtime' in dstat:
						entry['mtime_raw'] = dstat['mtime']
						entry['mtime']     = bargate.core.ut_to_string(dstat['mtime'])
					else:
						### No mtime?!?! wot.
						entry['mtime_raw'] = 0
						entry['mtime']     = '-'

					## URL to view the file, and downlad the file
					entry['view']     = url_for(func_name,path=entry['path'],action='view')
					entry['download'] = url_for(func_name,path=entry['path'],action='download')
					entry['default_open'] = entry['download']
					
					if 'size' in dstat:
						entry['size_raw'] = dstat['size']
						entry['size']     = bargate.core.str_size(dstat['size'])
					else:
						entry['size']     = '-'
						entry['size_raw'] = 0

					## File icon
					(ftype,mtype) = bargate.mime.filename_to_mimetype(entry['name'])
					entry['icon'] = bargate.mime.mimetype_to_icon(mtype)
					entry['mtype'] = ftype
					
					## Image previews
					if mtype.startswith('image'):
						entry['img_preview'] = url_for(func_name,path=entry['path'],action='preview')

					## View-in-browser download type
					if bargate.mime.view_in_browser(mtype):
						entry['bdownload'] = url_for(func_name,path=entry['path'],action='download',inbrowser='True')
						entry['default_open'] = entry['bdownload']
						
					## What to do based on 'on_file_click' setting
					on_file_click = bargate.settings.get_on_file_click()
					if on_file_click == 'ask':
						entry['on_file_click'] = ''
					elif on_file_click == 'default':
						entry['on_file_click'] = entry['default_open']
					elif on_file_click == 'download':
						entry['on_file_click'] = entry['download']
					
					## Append the file to the files list				
					files.append(entry)

				## DIRECTORY ###################################################
				elif dentry.smbc_type == bargate.smb.SMB_DIR:
					entry['icon'] = 'fa fa-fw fa-folder-open'	
					entry['type'] = 'dir'
					entry['view'] = url_for(func_name,path=entry['path'])
					entry['default_open'] = entry['view']
					dirs.append(entry)

				## SMB SHARE ###################################################
				elif dentry.smbc_type == bargate.smb.SMB_SHARE:
					## check last char for $
					last = entry['name'][-1]
					if last == "$":
						continue

					entry['icon'] = 'fa fa-fw fa-archive'
					entry['type'] = 'share'

					## url to view the share
					entry['view'] = url_for(func_name,path=entry['path'])
					entry['default_open'] = entry['view']

					files.append(entry)

			## Sort the directories and files by name
			dirs = sorted(dirs,cmp = bargate.core.sort_by_name)
			files = sorted(files,cmp = bargate.core.sort_by_name)

			## Combine dirs and files into one list
			entries = []
			for d in dirs:
				entries.append(d)
			for f in files:
				entries.append(f)

			## Build the URL to the parent directory
			## and the current directory name
			if len(path) > 0:
				(before,sep,after) = path.rpartition('/')
				if len(sep) > 0:
					cwd = after
					url_parent_dir = url_for(func_name,path=before)
				else:
					cwd = path
					url_parent_dir = url_for(func_name)
			else:
				cwd = ''
				url_parent_dir = ''

			## Build the refresh URL
			if len(path) > 0:
				url_refresh = url_for(func_name,path=path)
			else:
				url_refresh = url_for(func_name)

			## Build the root directory URL
			url_home=url_for(func_name)

			## Sort out the breadcrumb trail ##
			crumbs = []
			parts = path.split('/')
			b4 = ''

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
				
			## Bookmarks
			url_bookmark = url_for('bookmarks')

			if app.debug:
				filename = "directory-grid.html"
			else:
				filename = "directory.html"

			## Render the template
			return bargate.core.render_page(filename, 
				active=active,
				entries=entries,
				crumbs=crumbs,
				pwd=path,
				cwd=cwd,
				url_home=url_home,
				url_parent_dir=url_parent_dir,
				url_refresh=url_refresh,
				url_bookmark=url_bookmark,
				browse_mode=True,
				atroot = atroot,
				func_name = func_name,
				root_display_name = display_name,
				on_file_click=bargate.settings.get_on_file_click(),
			)

		else:
			abort(400)

	############################################################################
	## HTTP POST ACTIONS #######################################################
	# actions: unlink, mkdir, upload, rename
	############################################################################

	if request.method == 'POST':

		## Get the action requested
		action = request.form['action']

		## Get the path out of the form
		## and ignore the 'path' from the url
		path = request.form['path']
		
		## Check the path is valid
		try:
			bargate.smb.check_path(path)
		except ValueError as e:
			return bargate.errors.output_error('Invalid path',str(e))

		## pysmbc needs urllib quoted, but urllib can't handle unicode
		## so convert to str via encode utf8 and then urllib quote
		## it seems pysmbc can't handle unicode strings either anyway
		Spath = path.encode('utf8')
		Qpath = urllib.quote(Spath)

		## Build the URI
		uri = srv_path + path
		uri_as_str = srv_path.encode('utf8') + Qpath

		## Debug this for now
		app.logger.info('User "' + session['username'] + '" connected to "' + srv_path + '" using func name "' + func_name + '" and action "' + action + '" using POST and path "' + path + '" from "' + request.remote_addr + '" using ' + request.user_agent.string)
		
################################################################################
# UPLOAD FILE
################################################################################

		if action == 'jsonupload':
		
			ret = []
			
			uploaded_files = request.files.getlist("files[]")
			
			for file in uploaded_files:
			
				if bargate.core.banned_file(file.filename):
					ret.append({'name' : file.filename, 'error': 'Filetype not allowed'})
					continue
					
				## Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
				filename = bargate.core.secure_filename(file.filename)
				filename = filename.encode('utf8')
				filename = urllib.quote(filename)
				upload_uri = uri + '/' + filename

				## Check the new file name is valid
				try:
					bargate.smb.check_name(filename)
				except ValueError as e:
					ret.append({'name' : file.filename, 'error': 'Filename not allowed'})
					continue
					
				## Check to see if the file exists
				try:
					fstat = ctx.stat(upload_uri)
				except smbc.NoEntryError:
					## It doesn't exist so lets continue to upload
					pass
				except Exception as ex:
					ret.append({'name' : file.filename, 'error': 'Failed to stat existing file: ' + str(ex)})
					continue
					
				else:
					## If the file did exist, check to see if we should overwrite
					if fstat:
						if not bargate.settings.upload_overwrite():
							ret.append({'name' : file.filename, 'error': 'File already exists. You can enable overwriting files in Account Settings.'})
							continue

						## Now ensure we're not trying to upload a file on top of a directory (can't do that!)
						itemType = bargate.smb.getEntryType(ctx,upload_uri)
						if itemType == bargate.smb.SMB_DIR:
							ret.append({'name' : file.filename, 'error': "That name already exists and is a directory"})
							continue
			
				## Actual upload
				try:
					wfile = ctx.open(upload_uri,os.O_CREAT | os.O_WRONLY)
					data = file.read()
					wfile.write(data)
					wfile.close()

					ret.append({'name' : file.filename})

				except Exception as ex:
					ret.append({'name' : file.filename, 'error': 'Could not upload file: ' + str(ex)})
					continue
					
			for x in ret:
				app.logger.info('json stuff: ' + str(x))

			return jsonify({'files': ret})

		elif action == 'upload':

			error_redirect = redirect(url_for(func_name,path=path))

			ufile = request.files['file']
			if ufile:

				if not bargate.core.banned_file(ufile.filename):

					## Make the filename "secure" - see http://flask.pocoo.org/docs/patterns/fileuploads/#uploading-files
					filename = bargate.core.secure_filename(ufile.filename)
					filename = filename.encode('utf8')
					filename = urllib.quote(filename)
					upload_uri = uri + '/' + filename

					## Check the new file name is valid
					try:
						bargate.smb.check_name(filename)
					except ValueError as e:
						return bargate.errors.output_error('Invalid file name',str(e),error_redirect)

					## Check to see if the file exists
					try:
						fstat = ctx.stat(upload_uri)
					except smbc.NoEntryError:
						## It doesn't exist so lets continue to upload
						pass
					except Exception as ex:
						return bargate.errors.smbc_handler(ex,upload_uri,error_redirect)
					else:
						## If the file did exist, check to see if we should overwrite
						if fstat:
							overwrite = request.form.get('overwrite',default="")
							if overwrite <> 'overwrite':
								return bargate.errors.smbc_ExistsError(filename,error_redirect)

							## Now ensure we're not trying to upload a file on top of a directory (can't do that!)
							itemType = bargate.smb.getEntryType(ctx,uri_as_str)
							if itemType == bargate.smb.SMB_DIR:
								return bargate.errors.upload_overwrite_directory(error_redirect)
				
					## Actual upload
					try:
						wfile = ctx.open(upload_uri,os.O_CREAT | os.O_WRONLY)
						data = ufile.read()
						wfile.write(data)
						wfile.close()

						flash("The file '" + ufile.filename + "' was uploaded successfully.",'alert-success')
						return redirect(url_for(func_name,path=path))

					except Exception as ex:
						return bargate.errors.smbc_handler(ex,upload_uri,error_redirect)

				else:
					## INVALID FILE TYPE (BANNED)
					return bargate.errors.banned_file(error_redirect)
				
			else:
				## FILE NOT ATTACHED
				return bargate.errors.no_file_attached(error_redirect)

################################################################################
# RENAME FILE
################################################################################

		elif action == 'rename':

			## Pull the parent_dir out of the path
			(before,sep,after) = path.rpartition('/')
			if len(sep) > 0:
				parent_path = before
			else:
				parent_path = ""

			filename = after

			## Check the new file name is valid
			try:
				bargate.smb.check_name(request.form['newfilename'])
			except ValueError as e:
				return bargate.errors.output_error('Invalid file name',str(e))

			## build new URI
			newPath = request.form['newfilename'].encode('utf8')
			newPath = urllib.quote(newPath)
			newURI = srv_path + parent_path + '/' + newPath

			## the place to redirect to on success or failure
			redirect_path = redirect(url_for(func_name,path=parent_path))

			## get the item type of the existing 'filename'
			itemType = bargate.smb.getEntryType(ctx,uri_as_str)

			if itemType == bargate.smb.SMB_FILE:
				typemsg = "The file"
			elif itemType == bargate.smb.SMB_DIR:
				typemsg = "The directory"
			else:
				return bargate.errors.invalid_item_type(redirect_path)

			try:
				## uri_as_str is the existing quoted-encoded URI
				## newURI is the new URI which has been quoted-encoded
				ctx.rename(uri_as_str,newURI)
			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri,redirect_path)
			else:
				flash(typemsg + " '" + filename + "' was renamed to '" + request.form['newfilename'] + "' successfully.",'alert-success')
				return redirect_path

################################################################################
# COPY FILE
################################################################################

		elif action == 'copy':

			## Pull the filename out of the path
			(before,sep,after) = path.rpartition('/')
			if len(sep) > 0:
				before_path = srv_path + before
				filename = after
				error_redirect = redirect(url_for(func_name,path=before))
			else:
				before_path = srv_path
				filename = path
				error_redirect = redirect(url_for(func_name))

			try:
				## stat the source file first
				source_stat = ctx.stat(uri_as_str)

				## size of source
				source_size = source_stat[6]

				## determine item type
				itemType = bargate.smb.statToType(source_stat)

				## ensure item is a file
				if not itemType == SMB_FILE:
					return bargate.errors.invalid_item_copy(error_redirect)

			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri,error_redirect)

			## Get the new filename
			dest_filename = request.form['filename']
			
			## Check the new file name is valid
			try:
				bargate.smb.check_name(request.form['filename'])
			except ValueError as e:
				return bargate.errors.output_error('Invalid file name',str(e),error_redirect)
			
			## encode the new filename and quote the new filename
			dest = before_path + '/' + urllib.quote(dest_filename.encode('utf8'))

			## Make sure the dest file doesn't exist
			try:
				ctx.stat(dest)
			except smbc.NoEntryError as ex:
				## This is what we want - i.e. no file/entry
				pass
			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri,error_redirect)

			## Assuming we got here without an exception, open the source file
			try:		
				source_fh = ctx.open(uri_as_str)
			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri,error_redirect)

			## Assuming we got here without an exception, open the dest file
			try:		
				dest_fh = ctx.open(dest, os.O_CREAT | os.O_WRONLY | os.O_TRUNC )

			except Exception as ex:
				return bargate.errors.smbc_handler(ex,srv_path + dest,error_redirect)

			## try reading then writing blocks of data, then redirect!
			try:
				location = 0
				while(location >= 0 and location < source_size):
					chunk = source_fh.read(1024)
					dest_fh.write(chunk)
					location = source_fh.seek(1024,location)

			except Exception as ex:
				return bargate.errors.smbc_handler(ex,srv_path + dest,error_redirect)

			flash('A copy of "' + filename + '" was created as "' + dest_filename + '"','alert-success')
			return error_redirect

################################################################################
# MAKE DIR
################################################################################

		elif action == 'mkdir':
			## the place to redirect to on success or failure
			redirect_path = redirect(url_for(func_name,path=path))
			
			## Check the path is valid
			try:
				bargate.smb.check_name(request.form['directory_name'])
			except ValueError as e:
				return bargate.errors.output_error('Invalid folder name',str(e),redirect_path)

			## Take 'unicode' object and convert it into a byte string ('string' object)
			## Then quote it ready for SMB usage
			mkdirname = request.form['directory_name'].encode('utf8')
			mkdirname = urllib.quote(mkdirname)
			mkdir_uri = uri + '/' + mkdirname

			try:
				ctx.mkdir(mkdir_uri,0755)
			except Exception as ex:
				return bargate.errors.smbc_handler(ex,uri,redirect_path)
			else:
				flash("The folder '" + request.form['directory_name'] + "' was created successfully.",'alert-success')
				return redirect_path

################################################################################
# DELETE FILE
################################################################################

		elif action == 'unlink':
			uri = uri.encode('utf8')

			## We set the return path to the directory the file
			## is in, but we get sent the full uri. find the last /
			## and if there is anything after it...thats the filename, which
			## we tell the user is then deleted in a message. The rest is used
			## as the dir to redirect to.

			(before,sep,after) = path.rpartition('/')
			if len(sep) > 0:
			
				filename = after
				return_path = redirect(url_for(func_name,path=before))
			else:
				# directory ?
				filename = path
				return_path = redirect(url_for(func_name))

			error_return_path = return_path

			## was unlink called from view mode?
			try:
				if request.form['mode'] == 'view':
					error_return_path = redirect(url_for(func_name,action='view',path=path))
			except KeyError:
				pass

			## get the item type of the existing 'filename'
			itemType = bargate.smb.getEntryType(ctx,uri_as_str)

			if itemType == bargate.smb.SMB_FILE:
				try:
					ctx.unlink(uri_as_str)
				except Exception as ex:
					return bargate.errors.smbc_handler(ex,uri,error_return_path)
				else:
					flash("The file '" + filename + "' was deleted successfully.",'alert-success')
					return return_path
			elif itemType == bargate.smb.SMB_DIR:
				try:
					ctx.rmdir(uri_as_str)
				except Exception as ex:
					return bargate.errors.smbc_handler(ex,uri,error_return_path)
				else:
					flash("The directory '" + filename + "' was deleted successfully.",'alert-success')
					return return_path
			else:
				return bargate.errors.invalid_item_type(error_return_path)

		else:
			abort(400)

################################################################################
