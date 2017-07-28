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
from bargate import app
from flask import Flask, request, session, redirect, url_for, flash, g, abort, render_template, Response
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
				bargate.lib.userdata.save('layout',app.config['LAYOUT_DEFAULT'])
		else:
			bargate.lib.userdata.save('layout',app.config['LAYOUT_DEFAULT'])
						
		flash('Settings saved','alert-success')
		return redirect(url_for('settings'))

################################################################################

@app.route('/settings/layout',methods=['POST'])
@app.login_required
@app.allow_disable
def settings_set_layout():
	"""This is called by XHR to change the layout mode 'on the fly'. The browser
	calls it when the 'layout' button is clicked, and then the browser makes a
	fresh request to the server for the current directory."""

	if 'layout' in request.form:
		layout = request.form['layout']
		
		if layout == 'grid':
			bargate.lib.userdata.save('layout','grid')
		elif layout == 'list':
			bargate.lib.userdata.save('layout','list')
		else:
			bargate.lib.userdata.save('layout',app.config['LAYOUT_DEFAULT'])
	else:
		bargate.lib.userdata.save('layout',app.config['LAYOUT_DEFAULT'])

	return "", 200

################################################################################

@app.route('/settings.js')
@app.login_required
def settings_js():
		js = """var userLayout = "{0}";
var userToken = "{1}";
var userTheme = "{2}";
var userNavbar = "{3}";
""".format(bargate.lib.userdata.get_layout(),app.csrfp_token(),bargate.lib.userdata.get_theme(),bargate.lib.userdata.get_navbar())

		return Response(js, mimetype='application/javascript')

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
		
		if action == 'delete':
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
