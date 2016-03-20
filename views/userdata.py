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

import bargate
import bargate.lib.userdata
import bargate.lib.errors
import bargate.lib.smb
from bargate import app
from flask import Flask, request, session, redirect, url_for, flash, g, abort, render_template
import kerberos
import mimetypes
import os
from random import randint
import time
import json
import werkzeug

################################################################################
#### Account Settings View

@app.route('/settings', methods=['GET','POST'])
@app.login_required
@app.allow_disable
def settings():
	## Settings need redis storage, if redis is disabled we can't do settings :(
	if not app.config['REDIS_ENABLED']:
		abort(404)

	themes = []
	themes.append({'name':'Lumen','value':'lumen'})
	themes.append({'name':'Journal','value':'journal'})
	themes.append({'name':'Flatly','value':'flatly'})
	themes.append({'name':'Sandstone','value':'sandstone'})
	themes.append({'name':'Paper','value':'paper'})
	themes.append({'name':'Readable','value':'readable'})
	themes.append({'name':'Simplex','value':'simplex'})
	themes.append({'name':'Spacelab','value':'spacelab'})
	themes.append({'name':'United','value':'united'})
	themes.append({'name':'Cerulean','value':'cerulean'})
	themes.append({'name':'Darkly','value':'darkly'})
	themes.append({'name':'Cyborg','value':'cyborg'})
	themes.append({'name':'Slate','value':'slate'})


	if request.method == 'GET':
	
		if bargate.lib.userdata.get_show_hidden_files():
			hidden_files = 'show'
		else:
			hidden_files = 'hide'
			
		if bargate.lib.userdata.get_overwrite_on_upload():
			overwrite_on_upload = 'yes'
		else:
			overwrite_on_upload = 'no'
	
		return render_template('settings.html', 
			active='user',
			themes=themes,
			hidden_files=hidden_files,
			overwrite_on_upload = overwrite_on_upload,
			on_file_click = bargate.lib.userdata.get_on_file_click(),
		)

	elif request.method == 'POST':
	
		## Set theme
		new_theme = request.form['theme']
		
		## check theme is valid
		theme_set = False
		for theme in themes:
			if new_theme == theme['value']:
				bargate.lib.userdata.save('theme',new_theme)
				theme_set = True
				
		if not theme_set:
			flash('Invalid theme choice','alert-danger')
			return redirect(url_for('settings'))
			
		## navbar inverse/alt
		if 'navbar_alt' in request.form:
			navbar_alt = request.form['navbar_alt']
			if navbar_alt == 'inverse':
				bargate.lib.userdata.save('navbar_alt','inverse')
			else:
				bargate.lib.userdata.save('navbar_alt','default')
		else:
			bargate.lib.userdata.save('navbar_alt','default')
					
		## Set hidden files
		if 'hidden_files' in request.form:
			hidden_files = request.form['hidden_files']
			if hidden_files == 'show':
				bargate.lib.userdata.save('hidden_files','show')
			else:
				bargate.lib.userdata.save('hidden_files','hide')
		else:
			bargate.lib.userdata.save('hidden_files','hide')
			
		## Upload overwrite
		if 'overwrite_on_upload' in request.form:
			overwrite_on_upload = request.form['overwrite_on_upload']
			
			if overwrite_on_upload == 'yes':
				bargate.lib.userdata.save('upload_overwrite','yes')
			else:
				bargate.lib.userdata.save('upload_overwrite','no')
		else:
			bargate.lib.userdata.save('upload_overwrite','no')
			
		## On file click
		if 'on_file_click' in request.form:
			on_file_click = request.form['on_file_click']
			
			if on_file_click == 'download':
				bargate.lib.userdata.save('on_file_click','download')
			elif on_file_click == 'default':
				bargate.lib.userdata.save('on_file_click','default')
			else:
				bargate.lib.userdata.save('on_file_click','ask')
		else:
			bargate.lib.userdata.save('on_file_click','ask')
						
		flash('Settings saved','alert-success')
		return redirect(url_for('settings'))

################################################################################
#### BOOKMARKS

@app.route('/bookmarks', methods=['GET','POST'])
@app.login_required
@app.allow_disable
def bookmarks():
	## Bookmarks needs redis storage, if redis is disabled we can't do bookmarks
	if not app.config['REDIS_ENABLED']:
		abort(404)

	bmKey = 'user:' + session['username'] + ':bookmarks'
	bmPrefix = 'user:' + session['username'] + ':bookmark:'

	if request.method == 'GET':
		bookmarks = bargate.lib.userdata.get_bookmarks()
		return render_template('bookmarks.html', active='user',pwd='',bookmarks = bookmarks)
		
	elif request.method == 'POST':
		action = request.form['action']
		
		if action == 'add':
		
			try:
				bookmark_name     = request.form['bookmark_name']
				bookmark_function = bargate.lib.smb.check_name(request.form['bookmark_function'])
				bookmark_path     = bargate.lib.smb.check_path(request.form['bookmark_path'])
				
			except KeyError as e:
				bargate.lib.errors.fatal('Invalid bookmark','You missed something on the previous page!')
			except ValueError as e:
				bargate.lib.errors.fatal('Invalid bookmark','Invalid bookmark name or bookmark value: ' + str(e))
				
			try:
				test_name = url_for(str(bookmark_function),path=bookmark_path)
			except werkzeug.routing.BuildError as ex:
				bargate.lib.errors.fatal('Invalid bookmark','Invalid function bookmark path: ' + str(ex))

			g.redis.hset(bmPrefix + bookmark_name,'function',bookmark_function)
			g.redis.hset(bmPrefix + bookmark_name,'path',bookmark_path)
			g.redis.sadd(bmKey,bookmark_name)
		
			flash('Bookmark added successfully','alert-success')
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

@app.route('/online/<last>')
@app.login_required
@app.allow_disable
def online(last=5):
	last = int(last)

	if last == 1440:
		last_str = "24 hours"
	elif last == 60:
		last_str = "hour"
	elif last == 120:
		last_str = "2 hours"
	elif last == 180:
		last_str = "3 hours"
	else:
		last_str = str(last) + " minutes"			

	usernames = bargate.lib.userdata.get_online_users(last)
	return render_template('online.html',online=usernames,active="help",last=last_str)
