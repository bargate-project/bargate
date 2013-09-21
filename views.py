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
import bargate.core
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify, send_file
import re
import formencode
import kerberos
import smbc
import sys
import mimetypes
import socket
import os 
import json

################################################################################
#### HOME PAGE

@app.route('/')
@bargate.core.downtime_check
def hero():
	if 'username' in session:
		return redirect(url_for('personal'))
	else:
		next = request.args.get('next',default=None)
		return render_template('hero.html', active='hero',next=next)

################################################################################
#### ABOUT PAGE

@app.route('/about')
def about():
	return render_template('about.html', active='about')

@app.route('/about/changelog')
def changelog():
	return render_template('changelog.html', active='about')

################################################################################
#### LOGIN

@app.route('/login', methods=['GET','POST'])
def login():

	try:
		## Check password with kerberos
		kerberos.checkPassword(request.form['username'], request.form['password'], app.config['KRB5_SERVICE'], app.config['KRB5_DOMAIN'])
	except kerberos.BasicAuthError as e:
		flash('<strong>Error</strong> - Incorrect username and/or password','alert-error')
		return redirect(url_for('hero'))
	except kerberos.KrbError as e:
		flash('<strong>Unexpected Error</strong> - Kerberos Error: ' + e.__str__(),'error')
		return redirect(url_for('hero'))
	except kerberos.GSSError as e:
		flash('<strong>Unexpected Error</strong> - GSS Error: ' + e.__str__(),'error')
		return redirect(url_for('hero'))
	except Exception as e:
		bargate.errors.fatal(e)

	## Set logged in (if we got this far)
	session['logged_in'] = True
	session['username'] = request.form['username']

	## Check if the user selected "Log me out when I close the browser"
	permanent = request.form.get('sec',default="")

	## Set session as permanent or not
	if permanent == 'sec':
		session.permanent = True
	else:
		session.permanent = False

	## Set defaults for hidden files
	session['hidden_files'] = 'hide'
	
	## Encrypt the password and store in the session!
	try:
		session['id'] = bargate.core.aes_encrypt(request.form['password'],app.config['ENCRYPT_KEY'])
	except Exception as e:
		bargate.errors.fatal(e)

	## Log a successful login
	app.logger.info('User "' + session['username'] + '" logged in from "' + request.remote_addr + '" using ' + request.user_agent.string)

	# why on earth would we show this?
	#flash('<strong>Success!</strong> You were logged in successfully.','alert-success')

	## Put in a flash message for the survey
	flash('Please give us feedback by taking the <a href="https://www.isurvey.soton.ac.uk/8771">FWA Survey</a>','alert-info')

	## determine if "next" variable is set (the URL to be sent to)
	next = request.form.get('next',default=None)

	if next == None:
		return redirect(url_for('personal'))
	else:
		return redirect(next)

################################################################################
#### LOGOUT

@app.route('/logout')
@bargate.core.login_required
def logout():
	app.logger.info('User "' + session['username'] + '" logged out from "' + request.remote_addr + '" using ' + request.user_agent.string)

	session.pop('logged_in', None)
	session.pop('username', None)

	flash('<strong>Goodbye!</strong> - You were logged out','alert-success')

	return redirect(url_for('hero'))

################################################################################
#### MIME MAP (DEVELOPER FUNCTION)

@app.route('/mime')
@bargate.core.downtime_check
@bargate.core.login_required
def mime():
	ctx = smbc.Context(auth_fn=bargate.core.get_smbc_auth)
	test = bargate.smb.statURI(ctx,u"smb://filestore.soton.ac.uk/Users/" + unicode(session['username']) + '/fwa.tar.gz')
	return render_template("mime.html",types=mimetypes.types_map,test=test)

@app.route('/test')
@bargate.core.login_required
def test():
	return bargate.errors.output_error('title','message','errstr',redirect(url_for('mime')))

################################################################################
#### FILE VIEWS

@app.route('/personal', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def personal():
	return bargate.smb.connection(u"smb://filestore.soton.ac.uk/Users/" + unicode(session['username']) + '/',"personal")

@app.route('/webfiles', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def webfiles():
	return bargate.smb.connection(u"smb://webfiles.soton.ac.uk/" + unicode(session['username']) + '/',"webfiles")

@app.route('/soton', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def soton():
	return bargate.smb.connection(u"smb://soton.ac.uk/","soton")

@app.route('/filestore', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def filestore():
	return bargate.smb.connection(u"smb://filestore.soton.ac.uk/","filestore")

@app.route('/resource', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def resource():
    return bargate.smb.connection(u"smb://soton.ac.uk/resource/","resource")

@app.route('/linuxresearch', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def linuxresearch():
	return bargate.smb.connection(u"smb://linuxresearch.soton.ac.uk/","linuxresearch")

################################################################################
#### FAVOURITES / BOOKMARKS

@app.route('/bookmarks', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def bookmarks():
	## URLs for browsing around
	url_personal    = url_for('personal')
	url_mydocuments = url_for('personal',path='mydocuments')
	url_mydesktop   = url_for('personal',path='mydesktop')
	url_website     = url_for('webfiles')

	ctx = smbc.Context(auth_fn=bargate.core.get_smbc_auth)
	bmPath = u"smb://filestore.soton.ac.uk/Users/" + unicode(session['username']) + '/.fwabookmarks'

	try:
		bmFile = ctx.open(bmPath, os.O_CREAT | os.O_RDWR)
	except Exception as ex:
		 return bargate.errors.smbc_handler(ex)

	try:
		jsonData = json.load(bmFile)
	except TypeError as ex:
		## no json here, fix later.
		pass
	except Exception as ex:
		return bargate.errors.smbc_handler(ex)

	bmList = list()

	if type(jsonData) is dict:
		if 'bookmarks' in jsonData:
			#return bargate.errors.debugError(str(type(jsonData['bookmarks'])))
			for entry in jsonData['bookmarks']:
				if type(entry) is dict:
					if 'name' in entry and 'function' in entry and 'path' in entry:
						listEntry = { 'name': entry['name'], 'url': url_for(entry['function'],path=entry['path']) }
						bmList.append(listEntry)
	return render_template('bookmarks.html', active='bookmarks',pwd='',url_personal=url_personal,
				url_mydocuments=url_mydocuments,
				url_mydesktop=url_mydesktop,
				url_website=url_website,
				bookmarks = bmList)


################################################################################
#### CUSTOM FILE SHARE

@app.route('/other')
@bargate.core.login_required
@bargate.core.downtime_check
def other():
	## URLs for browsing around
	url_personal    = url_for('personal')
	url_mydocuments = url_for('personal',path='mydocuments')
	url_mydesktop   = url_for('personal',path='mydesktop')
	url_website     = url_for('webfiles')

	return render_template('other.html', active='other',pwd='',url_personal=url_personal,
				url_mydocuments=url_mydocuments,
				url_mydesktop=url_mydesktop,
				url_website=url_website)

@app.route('/custom', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def custom():

	if request.method == 'POST':
		try:
			server_uri = request.form['open_server_uri']
			## TODO validate the path...somehow

			session['custom_uri'] = server_uri
			session.modified = True
			## redirect to custom so its now a GET request
			return redirect(url_for('custom'))

		except KeyError as ex:
			## standard POST, not setting up a new server
			pass

	## ensure the custom_uri is set
	if 'custom_uri' in session:
		if len(session['custom_uri']) == 0:
			return redirect(url_for('other'))
	else:
		return redirect(url_for('other'))

	return bargate.smb.connection(unicode(session['custom_uri']),"custom")
