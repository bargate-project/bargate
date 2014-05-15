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

def get_user_theme():
	if 'username' in session: 
		try:
			theme = g.redis.get('user:' + session['username'] + ':theme')

			if theme != None:
				return theme
				
		except Exception as ex:
			## Can't return an error, this function is called from jinja.
			app.logger.error('Unable to speak to redis: ' + str(ex))

	## If we didn't return a new theme, return the default from the config file
	return app.config['THEME_DEFAULT']

################################################################################

def get_user_navbar():
	if 'username' in session:
		try:
			navbar = g.redis.get('user:' + session['username'] + ':navbar_alt')

			if navbar != None:
				return navbar
			else:
				return 'default'
					
		except Exception as ex:
			## Can't return an error, this function is called from jinja.
			app.logger.error('Unable to speak to redis: ' + str(ex))

	return 'default'

################################################################################

def show_hidden_files():
	if 'username' in session:
	
		## Get a cached response rather than asking REDIS every time
		hidden_files = g.get('hidden_files', None)
		if not hidden_files == None:
			return hidden_files
		else:
			try:
				hidden_files = g.redis.get('user:' + session['username'] + ':hidden_files')

				if hidden_files != None:
					if hidden_files == 'show':
						g.hidden_files = True
						return True

			except Exception as ex:
				app.logger.error('Unable to speak to redis: ' + str(ex))

	g.hidden_files = False
	return False
	
################################################################################

def upload_overwrite():
	if 'username' in session:
		try:
			upload_overwrite = g.redis.get('user:' + session['username'] + ':upload_overwrite')

			if upload_overwrite != None:
				if upload_overwrite == 'yes':
					return True

		except Exception as ex:
			app.logger.error('Unable to speak to redis: ' + str(ex))

	return False
	
################################################################################

def get_on_file_click():
	if 'username' in session:
	
		## Get a cached response rather than asking REDIS every time
		on_file_click = g.get('on_file_click', None)
		if not on_file_click == None:
			return on_file_click
		else:
			try:
				on_file_click = g.redis.get('user:' + session['username'] + ':on_file_click')

				if on_file_click != None:
					g.on_file_click = on_file_click
					return on_file_click
				else:
					g.on_file_click = 'ask'
					return 'ask'

			except Exception as ex:
				app.logger.error('Unable to speak to redis: ' + str(ex))

	g.on_file_click = 'ask'
	return 'ask'
	
################################################################################

def set_user_data(key,value):
	g.redis.set('user:' + session['username'] + ':' + key,value)
	
################################################################################

def get_user_bookmarks():
	bmKey = 'user:' + session['username'] + ':bookmarks'
	bmPrefix = 'user:' + session['username'] + ':bookmark:'
	bmList = list()
	
	if g.redis.exists(bmKey):
		try:
			bookmarks = g.redis.smembers(bmKey)
		except Exception as ex:	
			app.logger.error('Failed to load bookmarks for ' + session['username'] + ': ' + str(ex))
			return bmList

		if bookmarks != None:
			if isinstance(bookmarks,set):
				for bookmark_name in bookmarks:
	
					try:
						function = g.redis.hget(bmPrefix + bookmark_name,'function')
						path     = g.redis.hget(bmPrefix + bookmark_name,'path')
					except Exception as ex:
						app.logger.error('Failed to load bookmark ' + bookmark_name + ' for ' + session['username'] + ': ' + str(ex))
						continue
					
					if function == None:
						app.logger.error('Failed to load bookmark ' + bookmark_name + ' for ' + session['username'] + ': ', 'function was not set')
						continue
					if path == None:
						app.logger.error('Failed to load bookmark ' + bookmark_name + ' for ' + session['username'] + ': ', 'path was not set')
						continue
					
					try:
						bm = { 'name': bookmark_name, 'url': url_for(function,path=path) }
						bmList.append(bm)
					except werkzeug.routing.BuildError as ex:
						bargate.errors.fatal('Failed to load bookmark ' + bookmark_name + ': Invalid bookmark function and/or path - ', str(ex))
						continue
			else:
				app.logger.error('Failed to load bookmarks','Invalid redis data type when loading bookmarks set for ' + session['username'])
				
	return bmList

################################################################################
#### Account Settings View

@app.route('/settings', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def settings():

	themes = []
	themes.append({'name':'Lumen','value':'lumen'})
	themes.append({'name':'Journal','value':'journal'})
	themes.append({'name':'Flatly','value':'flatly'})
	themes.append({'name':'Readable','value':'readable'})
	themes.append({'name':'Simplex','value':'simplex'})
	themes.append({'name':'Spacelab','value':'spacelab'})
	themes.append({'name':'United','value':'united'})
	themes.append({'name':'Cerulean','value':'cerulean'})
	themes.append({'name':'Darkly','value':'darkly'})
	themes.append({'name':'Cyborg','value':'cyborg'})
	themes.append({'name':'Slate','value':'slate'})

	
	if request.method == 'POST':
	
		## Set theme
		new_theme = request.form['theme']
		
		## check theme is valid
		theme_set = False
		for theme in themes:
			if new_theme == theme['value']:
				bargate.settings.set_user_data('theme',new_theme)
				theme_set = True
				
		if not theme_set:
			flash('Invalid theme choice','alert-danger')
			return bargate.core.render_page('settings.html', active='user', themes=themes)
			
		## navbar inverse/alt
		if 'navbar_alt' in request.form:
			navbar_alt = request.form['navbar_alt']
			if navbar_alt == 'inverse':
				bargate.settings.set_user_data('navbar_alt','inverse')
			else:
				bargate.settings.set_user_data('navbar_alt','default')
		else:
			bargate.settings.set_user_data('navbar_alt','default')
					
		## Set hidden files
		if 'hidden_files' in request.form:
			hidden_files = request.form['hidden_files']
			if hidden_files == 'show':
				bargate.settings.set_user_data('hidden_files','show')
			else:
				bargate.settings.set_user_data('hidden_files','hide')
		else:
			bargate.settings.set_user_data('hidden_files','hide')
			
		## Upload overwrite
		if 'upload_overwrite' in request.form:
			upload_overwrite = request.form['upload_overwrite']
			
			if upload_overwrite == 'yes':
				bargate.settings.set_user_data('upload_overwrite','yes')
			else:
				bargate.settings.set_user_data('upload_overwrite','no')
		else:
			bargate.settings.set_user_data('upload_overwrite','no')
			
		## On file click
		if 'on_file_click' in request.form:
			on_file_click = request.form['on_file_click']
			
			if on_file_click == 'download':
				bargate.settings.set_user_data('on_file_click','download')
			elif on_file_click == 'default':
				bargate.settings.set_user_data('on_file_click','default')
			else:
				bargate.settings.set_user_data('on_file_click','ask')
		else:
			bargate.settings.set_user_data('on_file_click','ask')
						
		flash('Settings saved','alert-success')
		return redirect(url_for('settings'))
				
	elif request.method == 'GET':
	
		if bargate.settings.show_hidden_files():
			hidden_files = 'show'
		else:
			hidden_files = 'hide'
			
		if bargate.settings.upload_overwrite():
			upload_overwrite = 'yes'
		else:
			upload_overwrite = 'no'
	
		return bargate.core.render_page('settings.html', 
			active='user',
			themes=themes, 
			hidden_files=hidden_files,
			upload_overwrite=upload_overwrite,
			on_file_click = bargate.settings.get_on_file_click(),
		)

