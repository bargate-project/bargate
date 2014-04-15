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
from random import randint

################################################################################
#### HOME PAGE

@app.route('/')
@bargate.core.downtime_check
def hero():
	if 'username' in session:
		return redirect(url_for('personal'))
	else:
		next = request.args.get('next',default=None)

		## generate a background image to showz
		bgnumber = randint(1,17)

		return render_template('hero.html', next=next,bgnumber=bgnumber)

################################################################################
#### HELP PAGES

@app.route('/about')
def about():
	return bargate.core.render_page('about.html', active='help')

@app.route('/about/changelog')
def changelog():
	return bargate.core.render_page('changelog.html', active='help')

################################################################################
#### LOGIN

@app.route('/login', methods=['POST'])
def login():

	try:
		## Check password with kerberos
		kerberos.checkPassword(request.form['username'], request.form['password'], app.config['KRB5_SERVICE'], app.config['KRB5_DOMAIN'])
	except kerberos.BasicAuthError as e:
		flash('<strong>Error</strong> - Incorrect username and/or password','alert-danger')
		return redirect(url_for('hero'))
	except kerberos.KrbError as e:
		flash('<strong>Unexpected Error</strong> - Kerberos Error: ' + e.__str__(),'alert-danger')
		return redirect(url_for('hero'))
	except kerberos.GSSError as e:
		flash('<strong>Unexpected Error</strong> - GSS Error: ' + e.__str__(),'alert-danger')
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
	bargate.core.session_logout()
	flash('<strong>Goodbye!</strong> - You were logged out','alert-success')
	return redirect(url_for('hero'))

################################################################################
#### MIME MAP (DEVELOPER FUNCTION)

@app.route('/mime')
@bargate.core.downtime_check
@bargate.core.login_required
def mime():
	mimetypes.init()
	return bargate.core.render_page("mime.html",types=mimetypes.types_map,active="help")

################################################################################
#### FILE VIEWS

## SMB CONNECTION TAKES FOUR ARGS
## SMB path to start at
## function name (to allow url_for to be generated)
## 'active' part of the site, for the menu 'active' CSS
## 'display_name' - the name to show on the page to end users to show where they are

@app.route('/personal', methods=['GET','POST'], defaults={'path': ''})
@app.route('/personal/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def personal(path):
	return bargate.smb.connection(u"smb://filestore.soton.ac.uk/Users/" + unicode(session['username']) + '/',"personal", "home", "Home",path)

@app.route('/webfiles', methods=['GET','POST'], defaults={'path': ''})
@app.route('/webfiles/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def webfiles(path):
	return bargate.smb.connection(u"smb://webfiles.soton.ac.uk/" + unicode(session['username']) + '/',"webfiles", "home", "My Website",path)

@app.route('/soton', methods=['GET','POST'], defaults={'path': ''})
@app.route('/soton/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def soton(path):
	return bargate.smb.connection(u"smb://soton.ac.uk/","soton","shared","DFS Root", path)

@app.route('/filestore', methods=['GET','POST'], defaults={'path': ''})
@app.route('/filestore/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def filestore(path):
	return bargate.smb.connection(u"smb://filestore.soton.ac.uk/","filestore","shared","Isilon Root",path)

@app.route('/resource', methods=['GET','POST'], defaults={'path': ''})
@app.route('/resource/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def resource(path):
    return bargate.smb.connection(u"smb://soton.ac.uk/resource/","resource","shared","Resource Drive",path)

@app.route('/medis/shared', methods=['GET','POST'], defaults={'path': ''})
@app.route('/medis/shared/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def medis(path):
    return bargate.smb.connection(u"smb://rj-macleod.soton.ac.uk/medisdfs/","medis","shared", "MEDIS Shared",path)

@app.route('/medis/users', methods=['GET','POST'], defaults={'path': ''})
@app.route('/medis/users/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def medis_personal(path):
    return bargate.smb.connection(u"smb://rj-macleod.soton.ac.uk/users$/" + unicode(session['username']) + '/',"medis_personal","shared", "MEDIS Users",path)

@app.route('/linuxresearch', methods=['GET','POST'], defaults={'path': ''})
@app.route('/linuxresearch/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def linuxresearch(path):
	return bargate.smb.connection(u"smb://linuxresearch.soton.ac.uk/","linuxresearch","shared","Linux Research",path)

@app.route('/lamp1', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lamp1/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lamp1(path):
	return bargate.smb.connection(u"smb://lamp.soton.ac.uk/","lamp1","shared","LAMP Server 1",path)

@app.route('/lamp2', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lamp2/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lamp2(path):
	return bargate.smb.connection(u"smb://lamp2.soton.ac.uk/","lamp2","shared","LAMP Server 2",path)

@app.route('/lamp3', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lamp3/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lamp3(path):
	return bargate.smb.connection(u"smb://lamp3.soton.ac.uk/","lamp3","shared","LAMP Server 3",path)

@app.route('/lampx1', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lampx1/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lampx1(path):
	return bargate.smb.connection(u"smb://srv00521.soton.ac.uk/","lampx1","shared","LAMP-X server 1",path)

@app.route('/lampx2', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lampx2/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lampx2(path):
	return bargate.smb.connection(u"smb://srv00522.soton.ac.uk/","lampx2","shared","LAMP-X server 2",path)

@app.route('/lampx3', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lampx3/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lampx3(path):
	return bargate.smb.connection(u"smb://srv00523.soton.ac.uk/","lampx3","shared","LAMP-X server 3",path)

@app.route('/lampx4', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lampx4/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lampx4(path):
	return bargate.smb.connection(u"smb://srv00524.soton.ac.uk/","lampx4","shared","LAMP-X server 4",path)

@app.route('/lampx5', methods=['GET','POST'], defaults={'path': ''})
@app.route('/lampx5/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def lampx5(path):
	return bargate.smb.connection(u"smb://srv00525.soton.ac.uk/","lampx5","shared","LAMP-X server 5",path)

@app.route('/kdrive', methods=['GET','POST'], defaults={'path': ''})
@app.route('/kdrive/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def kdrive(path):
	return bargate.smb.connection(u"smb://soton.ac.uk/filestore/","kdrive","shared","Legacy K Drive",path)

################################################################################
#### FAVOURITES / BOOKMARKS

@app.route('/bookmarks', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def bookmarks():

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
	return bargate.core.render_page('bookmarks.html', active='bookmarks',pwd='',bookmarks = bmList)

#################################
#### Theme 

@app.route('/theme', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def theme():
	## define the themes!
	themes = []
	themes.append({'name':'Lumen (Default)','value':'lumen'})
	themes.append({'name':'Journal','value':'journal'})
	themes.append({'name':'Flatly','value':'flatly'})
	themes.append({'name':'Readable','value':'readable'})
	themes.append({'name':'Simplex','value':'simplex'})
	themes.append({'name':'Spacelab','value':'spacelab'})
	themes.append({'name':'United','value':'united'})
	themes.append({'name':'Cerulean','value':'cerulean'})

	if request.method == 'POST':
		new_theme = request.form['theme']
		for theme in themes:
			if new_theme == theme['value']:
				session['theme'] = new_theme
				flash('Theme preference changed','alert-success')
				return redirect(url_for('personal'))
				
		flash('Invalid theme choice','alert-danger')
		return bargate.core.render_page('theme.html', active='user', themes=themes)
				
	elif request.method == 'GET':
		return bargate.core.render_page('theme.html', active='user', themes=themes)

################################################################################
#### CUSTOM FILE SHARE

@app.route('/other')
@bargate.core.login_required
@bargate.core.downtime_check
def other():
	return bargate.core.render_page('other.html', active='shared',pwd='')

@app.route('/custom')
@bargate.core.login_required
@bargate.core.downtime_check
def custom_server():
	return bargate.core.render_page('custom.html', active='shared',pwd='')

@app.route('/c', methods=['GET','POST'], defaults={'path': ''})
@app.route('/c/<path:path>/', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def custom(path):

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
			return redirect(url_for('custom_server'))
	else:
		return redirect(url_for('custom_server'))

	return bargate.smb.connection(unicode(session['custom_uri']),"custom","shared",session['custom_uri'],path)
