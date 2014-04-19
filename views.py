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
from flask import Flask, request, session, redirect, url_for, render_template, flash
import kerberos
import mimetypes
import os 
from random import randint

################################################################################
#### HOME PAGE / LOGIN PAGE

@app.route('/', methods=['GET', 'POST'])
@bargate.core.downtime_check
def login():
	if 'username' in session:
		return redirect(url_for('personal'))
	else:
		if request.method == 'GET':
			next = request.args.get('next',default=None)
			bgnumber = randint(1,17)
			return render_template('login.html', next=next,bgnumber=bgnumber)

		elif request.method == 'POST':

			try:
				## Check password with kerberos
				kerberos.checkPassword(request.form['username'], request.form['password'], app.config['KRB5_SERVICE'], app.config['KRB5_DOMAIN'])
			except kerberos.BasicAuthError as e:
				flash('<strong>Error</strong> - Incorrect username and/or password','alert-danger')
				return redirect(url_for('login'))
			except kerberos.KrbError as e:
				flash('<strong>Unexpected Error</strong> - Kerberos Error: ' + e.__str__(),'alert-danger')
				return redirect(url_for('login'))
			except kerberos.GSSError as e:
				flash('<strong>Unexpected Error</strong> - GSS Error: ' + e.__str__(),'alert-danger')
				return redirect(url_for('login'))

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
			session['id'] = bargate.core.aes_encrypt(request.form['password'],app.config['ENCRYPT_KEY'])

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
	return redirect(url_for('login'))

################################################################################
#### HELP PAGES

@app.route('/about')
def about():
	return bargate.core.render_page('about.html', active='help')

@app.route('/about/changelog')
def changelog():
	return bargate.core.render_page('changelog.html', active='help')

@app.route('/nojs')
def nojs():
	return bargate.core.render_page('nojs.html')

################################################################################
#### MIME MAP (DEVELOPER FUNCTION)

@app.route('/mime')
@bargate.core.downtime_check
@bargate.core.login_required
def mime():
	mimetypes.init()
	return bargate.core.render_page("mime.html",types=mimetypes.types_map,active="help")

################################################################################
#### BOOKMARKS (NOT YET IN USE)

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

################################################################################
#### THEME CHANGE

@app.route('/theme', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def theme():
	## define the themes!
	themes = []
	themes.append({'name':'Lumen','value':'lumen'})
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
				bargate.core.set_user_theme(new_theme)
				flash('Theme preference changed','alert-success')
				return redirect(url_for('personal'))
				
		flash('Invalid theme choice','alert-danger')
		return bargate.core.render_page('theme.html', active='user', themes=themes)
				
	elif request.method == 'GET':
		return bargate.core.render_page('theme.html', active='user', themes=themes)

