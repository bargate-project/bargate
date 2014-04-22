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
from flask import Flask, request, session, redirect, url_for, render_template, flash, g, abort
import kerberos
import mimetypes
import os 
from random import randint
import time
import json

################################################################################
#### HOME PAGE / LOGIN PAGE

@app.route('/', methods=['GET', 'POST'])
@bargate.core.downtime_check
def login():
	if 'username' in session:
		return redirect(url_for('personal'))
	else:
		if request.method == 'GET' or request.method == 'HEAD':
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

			## Encrypt the password and store in the session!
			session['id'] = bargate.core.aes_encrypt(request.form['password'],app.config['ENCRYPT_KEY'])

			## Log a successful login
			app.logger.info('User "' + session['username'] + '" logged in from "' + request.remote_addr + '" using ' + request.user_agent.string)

			## determine if "next" variable is set (the URL to be sent to)
			next = request.form.get('next',default=None)
			
			## Record the last login time
			bargate.core.set_user_data('login',str(time.time()))

			if next == None:
				return redirect(url_for('personal'))
			else:
				return redirect(next)

################################################################################
#### LOGOUT

@app.route('/logout')
@bargate.core.login_required
def logout():
	## Record 
	bargate.core.set_user_data('logout',str(time.time()))
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
	bmKey = 'user:' + session['username'] + ':bookmarks'
	bmPrefix = 'user:' + session['username'] + ':bookmark:'

	## todo: much better input verification

	if request.method == 'GET':
		bmList = list()
			
		if g.redis.exists(bmKey):
			try:
				bookmarks = g.redis.smembers(bmKey)
			except Exception as ex:
				bargate.errors.fatal('Failed to load bookmarks: ',str(ex))
	
			if bookmarks != None:
				if isinstance(bookmarks,set):
					for bookmark_name in bookmarks:
			
						try:
							function = g.redis.hget(bmPrefix + bookmark_name,'function')
							path     = g.redis.hget(bmPrefix + bookmark_name,'path')
						except Exception as ex:
							bargate.errors.fatal('Failed to load bookmark ' + bookmark_name + ': ', str(ex))
							
						if function == None:
							bargate.errors.fatal('Failed to load bookmark ' + bookmark_name + ': ', 'function was not set')
						if path == None:
							bargate.errors.fatal('Failed to load bookmark ' + bookmark_name + ': ', 'path was not set')
							
						try:
							bm = { 'name': bookmark_name, 'url': url_for(function,path=path) }
							bmList.append(bm)
						except werkzeug.routing.BuildError as ex:
							bargate.errors.fatal('Failed to load bookmark ' + bookmark_name + ': Invalid bookmark function and/or path - ', str(ex))
				else:
					bargate.errors.fatal('Failed to load bookmarks','Invalid redis data type when loading bookmarks set')

		return bargate.core.render_page('bookmarks.html', active='user',pwd='',bookmarks = bmList)
		
	elif request.method == 'POST':
		
		action = request.form['action']
		
		if action == 'add':
		
			## TODO really need to do some regex on the input here...
				## and you know, elsewhere? maybe? eugh. what about unicode though?
				## maybe just check for known invalid chars? eugh.
				## also check by building the url with url_for first... that'll verify function at least.
		
			bookmark_name     = request.form['bookmark_name']
			bookmark_function = request.form['bookmark_function']
			bookmark_path     = request.form['bookmark_path']
		
			g.redis.hset(bmPrefix + bookmark_name,'function',bookmark_function)
			g.redis.hset(bmPrefix + bookmark_name,'path',bookmark_path)
			g.redis.sadd(bmKey,bookmark_name)
		
			flash('Bookmark added successfully. <a href="' + url_for('bookmarks') + '">Click here to view your bookmarks.</a>','alert-success')
			## return the user to the folder they were in
			return redirect(url_for(bookmark_function,path=bookmark_path))
			
		elif action == 'delete':
			bookmark_name     = request.form['bookmark_name']
			
			if g.redis.exists(bmKey):
				if g.redis.sismember(bmKey,bookmark_name):
				
					## Delete from the bookmarks key
					g.redis.srem(bmKey,bookmark_name)
					
					## Delete the bookmark hash
					g.redis.delete(bmPrefix + bookmark_name)
					
					## Let the user know and redirect
					flash('Bookmark deleted successfully','alert-success')
					return redirect(url_for('bookmarks'))

			flash('Bookmark not found!','alert-danger')
			return redirect(url_for('bookmarks'))					
				
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
				bargate.core.set_user_data('theme',new_theme)
				flash('Theme preference changed','alert-success')
				return redirect(url_for('personal'))
				
		flash('Invalid theme choice','alert-danger')
		return bargate.core.render_page('theme.html', active='user', themes=themes)
				
	elif request.method == 'GET':
		return bargate.core.render_page('theme.html', active='user', themes=themes)

