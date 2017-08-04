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
from bargate.lib.userdata import themes
import bargate.lib.errors
from bargate import app
from flask import Flask, request, session, redirect, url_for, flash, g, abort
from flask import render_template, Response, jsonify
import werkzeug

@app.route('/settings', methods=['POST'])
@app.login_required
@app.allow_disable
def settings():
	## Settings need redis storage, if redis is disabled we can't do settings
	if not app.config['REDIS_ENABLED']:
		abort(404)

	key   = request.form['key']
	value = request.form['value']

	if key == 'layout':
		if value not in ['grid', 'list']:
			value = app.config['LAYOUT_DEFAULT']
		bargate.lib.userdata.save('layout',value)

	elif key == 'click':
		if value not in ['ask', 'default', 'download']:
			value = 'ask'
		bargate.lib.userdata.save('on_file_click',value)

	elif key == 'hidden':
		if value == 'true':
			bargate.lib.userdata.save('hidden_files','show')
		else:
			bargate.lib.userdata.save('hidden_files','hide')

	elif key == 'overwrite':
		if value == 'true':
			bargate.lib.userdata.save('upload_overwrite','yes')
		else:
			bargate.lib.userdata.save('upload_overwrite','no')

	elif key == 'theme':
		if value in themes.keys():
			bargate.lib.userdata.save('theme',value)
		else:
			bargate.lib.userdata.save('theme',app.config['THEME_DEFAULT'])
		return jsonify({'navbar': themes[value]})

	return "", 200

################################################################################

@app.route('/settings.js')
@app.login_required
def settings_js():

	if bargate.lib.userdata.get_show_hidden_files():
		show_hidden = 'true'
	else:
		show_hidden = 'false'

	if bargate.lib.userdata.get_overwrite_on_upload():
		overwrite = 'true'
	else:
		overwrite = 'false'

	js = """var $user = {{
	layout: "{0}",
	token: "{1}",
	theme: "{2}",
	navbar: "{3}",
	hidden: {4},
	overwrite: {5},
	onclick: "{6}"}};
""".format(bargate.lib.userdata.get_layout(),
		app.csrfp_token(),
		bargate.lib.userdata.get_theme(),
		bargate.lib.userdata.get_theme_navbar(),
		show_hidden,
		overwrite,
		bargate.lib.userdata.get_on_file_click())

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
		return render_template('bookmarks.html', active='user',
			pwd='', bookmarks = bookmarks)
		
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
				g.redis.hset(user_bookmark_prefix + bookmark_id,
					"name",
					bookmark_name)
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

	if not app.config['REDIS_ENABLED']:
		abort(404)

	## Prepare the redis key name
	redis_key = 'user:' + session['username'] + ':bookmark:' + bookmark_id

	## bookmarks are a hash with the keys 'version', 'function', 'path' and 
	## 'custom_uri' (optional) only proceed if we can find the bmark in redis
	if g.redis.exists(redis_key):
		try:
			# redis returns 'None' for hget if the hash key doesn't exist
			bookmark_version    = g.redis.hget(redis_key,'version')
			bookmark_function   = g.redis.hget(redis_key,'function')
			bookmark_path       = g.redis.hget(redis_key,'path')
			bookmark_custom_uri = g.redis.hget(redis_key,'custom_uri')
		except Exception as ex:
			app.logger.error('Failed to load v2 bookmark ' + bookmark_id + 
				' user: ' + session['username'] + ' error: ' + str(ex))
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
	return render_template('online.html',
		online=usernames,
		active="help",
		last=last_str)
