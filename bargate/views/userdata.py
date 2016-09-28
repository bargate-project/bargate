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
import mimetypes
import os
from random import randint
import time
import json
import werkzeug
import uuid

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
	themes.append({'name':'Cerulean','value':'cerulean'})
	themes.append({'name':'Cosmo','value':'cosmo'})
	themes.append({'name':'Cyborg','value':'cyborg'})
	themes.append({'name':'Journal','value':'journal'})
	themes.append({'name':'Flatly','value':'flatly'})
	themes.append({'name':'Sandstone','value':'sandstone'})
	themes.append({'name':'Paper','value':'paper'})
	themes.append({'name':'Readable','value':'readable'})
	themes.append({'name':'Simplex','value':'simplex'})
	themes.append({'name':'Spacelab','value':'spacelab'})
	themes.append({'name':'United','value':'united'})
	themes.append({'name':'Darkly','value':'darkly'})
	themes.append({'name':'Slate','value':'slate'})
	themes.append({'name':'Yeti','value':'yeti'})


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

		## Layout
		if 'layout' in request.form:
			layout = request.form['layout']
			
			if layout == 'grid':
				bargate.lib.userdata.save('layout','grid')
			elif layout == 'list':
				bargate.lib.userdata.save('layout','list')
		else:
			bargate.lib.userdata.save('layout','list')
						
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

	user_bookmarks_key   = 'user:' + session['username'] + ':bookmarks'
	user_bookmark_prefix = 'user:' + session['username'] + ':bookmark:'

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
				return bargate.lib.errors.stderr('Invalid bookmark','You missed something on the previous page!')
			except ValueError as e:
				return bargate.lib.errors.stderr('Invalid bookmark','Invalid bookmark name or bookmark value: ' + str(e))
			
			## Ensure that the function passed is a valid function	
			try:
				test_name = url_for(str(bookmark_function),path=bookmark_path)
			except werkzeug.routing.BuildError as ex:
				return bargate.lib.errors.stderr('Invalid bookmark','Invalid function bookmark path: ' + str(ex))

			## Generate a unique identifier for this bookmark
			bookmark_id = uuid.uuid4().hex
			
			## Update the user_bookmark_prefix with the ID
			user_bookmark_prefix = user_bookmark_prefix + bookmark_id

			## Mark this as a version 2 bookmark (v1.5 or later)
			g.redis.hset(user_bookmark_prefix,'version','2')

			## store the function name in use
			g.redis.hset(user_bookmark_prefix,'function',bookmark_function)

			## if we're on a custom server then we need to store the URL 
			## to that server otherwise the bookmark is useless.
			if bookmark_function == 'custom':
				if 'custom_uri' in session:
					g.redis.hset(user_bookmark_prefix,'custom_uri',session['custom_uri'])
				else:
					## the function is custom, but there is no custom_uri
					## so we should redirect the user to go choose one
					return redirect(url_for('custom_server'))

			## store the path the user is at within the share/function
			g.redis.hset(user_bookmark_prefix,'path',bookmark_path)

			## store the name/title of the bookmark
			g.redis.hset(user_bookmark_prefix,'name',bookmark_name)

			## add the new bookmark name to the list of bookmarks for the user
			g.redis.sadd(user_bookmarks_key,bookmark_id)

			flash('Bookmark added successfully','alert-success')
			return redirect(url_for(bookmark_function,path=bookmark_path))
			
		elif action == 'delete':
			bookmark_id     = request.form['bookmark_id']
			
			if g.redis.exists(user_bookmarks_key):
				if g.redis.sismember(user_bookmarks_key,bookmark_id):
				
					## Delete from the bookmarks key
					g.redis.srem(user_bookmarks_key,bookmark_id)
					
					## Delete the bookmark hash
					g.redis.delete(user_bookmark_prefix + bookmark_id)
					
					## Let the user know and redirect
					flash('Bookmark deleted successfully','alert-success')
					return redirect(url_for('bookmarks'))

			flash('Bookmark not found!','alert-danger')
			return redirect(url_for('bookmarks'))

		elif action == 'rename':
			bookmark_id     = request.form['bookmark_id']
			bookmark_name   = request.form['bookmark_name']
			
			if g.redis.exists(user_bookmark_prefix + bookmark_id):
				g.redis.hset(user_bookmark_prefix + bookmark_id,"name",bookmark_name)
				flash('Bookmark renamed successfully','alert-success')
				return redirect(url_for('bookmarks'))

			flash('Bookmark not found!','alert-danger')
			return redirect(url_for('bookmarks'))


################################################################################

@app.route('/bookmark/<string:bookmark_id>')
@app.login_required
@app.allow_disable
def bookmark(bookmark_id):
	"""This function takes a bookmark ID and redirects the user to the location
	specified by the bookmark in the REDIS database. This only works with 
	version 2 bookmarks, not version 1 (Bargate v1.4 or earlier)"""

	## Bookmarks needs redis storage, if redis is disabled we can't do bookmarks
	if not app.config['REDIS_ENABLED']:
		abort(404)

	## Prepare the redis key name
	redis_key = 'user:' + session['username'] + ':bookmark:' + bookmark_id

	## bookmarks are a hash with the keys 'version', 'function', 'path' and 'custom_uri' (optional)
	# only proceed if we can find the bookmark in redis
	if g.redis.exists(redis_key):
		try:
			# redis returns 'None' for hget if the hash key doesn't exist
			bookmark_version    = g.redis.hget(redis_key,'version')
			bookmark_function   = g.redis.hget(redis_key,'function')
			bookmark_path       = g.redis.hget(redis_key,'path')
			bookmark_custom_uri = g.redis.hget(redis_key,'custom_uri')
		except Exception as ex:
			app.logger.error('Failed to load v2 bookmark ' + bookmark_id + ' user: ' + session['username'] + ' error: ' + str(ex))
			abort(404)

		if bookmark_version is None:
			abort(404)

		if bookmark_version != '2':
			abort(404)

		## Handle custom URI bookmarks
		if bookmark_function == 'custom':
			# Set the custom_uri in the session so when the custom function is
			# hit then the user is sent to the right place (maybe)
			session['custom_uri'] = bookmark_custom_uri
			session.modified      = True

			# redirect the user to the custom function
			return redirect(url_for('custom',path=bookmark_path))

		## Handle standard non-custom bookmarks
		else:
			try:
				return redirect(url_for(bookmark_function,path=bookmark_path))
			except werkzeug.routing.BuildError as ex:
				## could not build a URL for that function_name
				## it could be that the function was removed by the admin
				## so we should say 404 not found.
				abort(404)

	else:
		## bookmark not found
		abort(404)

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
