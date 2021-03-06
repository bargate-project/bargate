#!/usr/bin/python
# -*- coding: utf-8 -*-
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
import bargate.lib.user
from flask import Flask, request, session, g, redirect, url_for, flash, render_template, make_response
import smbc
import traceback

################################################################################

## standard error (uses render_template and thus standard page layout)
def stderr(title,message,redirect_to=None):
	"""This function is called by other error functions to show the error to the
	end user. It takes a title, message and a further error type. If redirect
	is set then rather than show an error it will return the 'redirect' after
	setting the popup error flags so that after the redirect a popup error is 
	shown to the user. Redirect should be a string returned from flask redirect().
	"""
	
	debug = ""
	
	if app.debug:
		if app.config['DEBUG_FULL_ERRORS']:
			debug = traceback.format_exc()
			redirect_to = None
			
	if redirect_to == None:
		return render_template('error.html',title=title,message=message,debug=debug), 200
	else:
		## Set error modal and return
		app.set_modal_error(title,message)
		return redirect_to

################################################################################

## fatal error (returns HTML from python code - which is more likely to work)
def fatalerr(title=u"fatal error ☹",message="Whilst processing your request an unexpected error occured which the application could not recover from",debug=""):
	# Build the response. Not using a template here to prevent any Jinja 
	# issues from causing this to fail.
	html = u"""
<!doctype html>
<html>
<head>
	<title>Fatal Error</title>
	<meta charset="utf-8" />
	<meta http-equiv="Content-type" content="text/html; charset=utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1" />
	<style type="text/css">
	body {
		background-color: #8B1820;
		color: #FFFFFF;
		margin: 0;
		padding: 0;
		font-family: "Open Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
	}
	h1 {
		font-size: 4em;
		font-weight: normal;
		margin: 0px;
	}
	div {
		width: 80%%;
		margin: 5em auto;
		padding: 50px;
		border-radius: 0.5em;
    }
    @media (max-width: 900px) {
        div {
            width: auto;
            margin: 0 auto;
            border-radius: 0;
            padding: 1em;
        }
    }
    </style>    
</head>
<body>
<div>
	<h1>%s</h1>
	<p>%s</p>
	<pre>%s</pre>
</div>
</body>
</html>
""" % (title,message,debug)

	return make_response(html, 500)

################################################################################

## handler for all exceptions generated by pysmbc
def smbc_handler(exception_object,uri="Unknown",redirect_to=None):
	"""Handles exceptions generated by pysmbc functions. It currently deals with
	all known smbc exceptions. This will generate fancy formatted messages
	for each smbc type.
	"""

	# PERMISSION DENIED
	if isinstance(exception_object,smbc.PermissionError):
		return smbc_PermissionDenied(redirect_to)

	# NO ENTRY (doesn't exist)
	elif isinstance(exception_object,smbc.NoEntryError):
		return smbc_NoEntryError(uri,redirect_to)

	# NO SPACE LEFT ON DEVICE
	elif isinstance(exception_object,smbc.NoSpaceError):
		return smbc_NoSpaceError(redirect_to)

	# FILE OR DIR ALREADY EXISTS
	elif isinstance(exception_object,smbc.ExistsError):
		return smbc_ExistsError(uri,redirect_to)

	# DIRECTORY NOT EMPTY
	elif isinstance(exception_object,smbc.NotEmptyError):
		return smbc_NotEmptyError(uri,redirect_to)

	# TIMED OUT
	elif isinstance(exception_object,smbc.TimedOutError):
		return smbc_TimedOutError(redirect_to)

	# CONNECTION REFUSED
	elif isinstance(exception_object,smbc.ConnectionRefusedError):
		return smbc_ConnectionRefusedError(redirect_to)
		
	# pysmbc spits out RuntimeError when everything else fails
	elif isinstance(exception_object,RuntimeError):
		return smbc_RuntimeError(redirect_to)

	# ALL OTHER EXCEPTIONS
	else:
		return bargate.views.errors.error500(exception_object)

## pysmbc errors

def smbc_NoEntryError(uri,redirect_to=None):
	"""Prints out a nice error for smbc.NoEntryError exceptions"""
	return stderr("No such file or directory","The file or directory '" + uri + "' was not found.",redirect_to)

def smbc_NotEmptyError(uri,redirect_to=None):
	"""Prints out a nice error for smbc.NotEmptyError exceptions"""
	return stderr("The directory is not empty","The directory '" + uri + "' is not empty so cannot be deleted.",redirect_to)

def smbc_PermissionDenied(redirect_to=None):
	"""Prints out a nice error for smbc.PermissionDenied exceptions"""
	
	## Test to see if the password has changed since logon which would mean perm denied was password related
	result = bargate.lib.user.auth(session['username'], bargate.lib.user.get_password())
	if not result:
		bargate.lib.user.logout()
		flash('Your password has changed. You must login again.','alert-danger')
		return redirect(url_for('login'))
	
	return stderr("Permission Denied","You do not have permission to perform the action.",redirect_to)

def smbc_ExistsError(uri,redirect_to=None):
	"""Prints out a nice error for smbc.ExistsError exceptions"""
	return stderr("File or directory already exists","The file or directory '" + uri + "' which you attempted to create already exists.",redirect_to)

def smbc_NoSpaceError(redirect_to=None):
	"""Prints out a nice error for smbc.NoSpaceError exceptions"""
	return stderr("No space left on device","There is no space left on the server. You may have exceeded your usage allowance/quota.",redirect_to)

def smbc_TimedOutError(redirect_to=None):
	"""Prints out a nice error for smbc.TimedOutError exceptions"""
	return stderr("Timed out","The current operation timed out. Please try again later.",redirect_to)
	
def smbc_RuntimeError(redirect_to=None):
	"""Prints out a nice error for RuntimeError when smbc is called"""
	return stderr("File Server Error","An unknown error was returned from the file server. Please contact your support team.",redirect_to)

def smbc_ConnectionRefusedError(redirect_to=None):
	"""Prints out a nice error for smbc.ConnectionRefusedError"""
	return stderr("Connection Refused","The remote server refused our connection. Check the custom server address and try again",redirect_to)

## Bargate internal errors

def banned_file(redirect_to=None):
	"""Returns a template or redirect to return from the view for when a banned file is uploaded.
	"""
	return stderr("Banned File Type","The file type you are trying to upload is banned from being uploaded.",redirect_to)

def no_file_attached(redirect_to=None):
	"""Returns a template or redirect to return from the view for when no file is attached during an upload.
	"""
	return stderr("No file attached","You did not attach a file when attempting to upload",redirect_to)

def upload_file_directory(redirect_to=None):
	"""Returns a template or redirect to return from the view for when a user tries to upload a file over the top of a directory (file upload name is same as existing directory name)
	"""
	return stderr("Unable to upload file","A directory already exists with the same name as the file you are trying to upload.",redirect_to)

def invalid_item_type(redirect_to=None):
	"""Returns a template or redirect to return from the view for when an action is performed on an invalid item type.
	"""
	return stderr("Invalid item type","You tried to perform an action on an invalid item type - i.e. a share or printer.",redirect_to)

def invalid_item_download(redirect_to=None):
	"""Returns a template or redirect to return from the view for when an item is downloaded which isn't a file.
	"""
	return stderr("Invalid item type","You tried to download an item other than a file.",redirect_to)

def invalid_item_copy(redirect_to=None):
	"""Returns a template or redirect to return from the view for when a user tries to copy an item other than a file.
	"""
	return stderr("Invalid item type","You tried to copy an item other than a file.",redirect_to)

def invalid_path(redirect_to=None):
	"""Returns a template or redirect to return from the view for when a user navigates to an invalid path."""
	return stderr("Invalid path","You tried to navigate to an invalid or illegal path.",redirect_to)

def invalid_name(redirect_to=None):
	"""Returns a template or redirect to return from the view for when a user enters an invalid file name"""
	return stderr("Invalid file or directory name","The file or directory name you entered is invalid",redirect_to)
