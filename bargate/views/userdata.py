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

from flask import request, session, redirect, url_for, flash, g, abort, render_template, jsonify
import werkzeug

from bargate.lib import userdata
from bargate import app


@app.route('/xhr/settings', methods=['GET', 'POST'])
@app.set_response_type('json')
def settings():
	if request.method == 'GET':

		if userdata.get_show_hidden_files():
			show_hidden = 'true'
		else:
			show_hidden = 'false'

		if userdata.get_overwrite_on_upload():
			overwrite = 'true'
		else:
			overwrite = 'false'

		return(jsonify({'code': 0,
			'layout': userdata.get_layout(),
			'token': app.csrfp_token(),
			'theme': userdata.get_theme(),
			'navbar': userdata.get_theme_navbar(),
			'hidden': show_hidden,
			'overwrite': overwrite,
			'onclick': userdata.get_on_file_click()}))

	else:

		if not app.is_user_logged_in():
			return jsonify({'code': 401, 'msg': 'You must be logged in to do that'})

		if not app.config['REDIS_ENABLED']:
			return jsonify({'code': 1, 'msg': 'The system administrator has disabled per-user settings'})

		key   = request.form['key']
		value = request.form['value']

		if key == 'layout':
			if value not in ['grid', 'list']:
				value = app.config['LAYOUT_DEFAULT']
			userdata.save('layout', value)

		elif key == 'click':
			if value not in ['ask', 'default', 'download']:
				value = 'ask'
			userdata.save('on_file_click', value)

		elif key == 'hidden':
			if value == 'true':
				userdata.save('hidden_files', 'show')
			else:
				userdata.save('hidden_files', 'hide')

		elif key == 'overwrite':
			if value == 'true':
				userdata.save('upload_overwrite', 'yes')
			else:
				userdata.save('upload_overwrite', 'no')

		elif key == 'theme':
			if value not in userdata.themes.keys():
				value = app.config['THEME_DEFAULT']

			userdata.save('theme', value)
			return jsonify({'code': 0, 'navbar': userdata.themes[value]})

		return jsonify({'code': 0})


@app.route('/bookmarks', methods=['GET', 'POST'])
@app.login_required
def bookmarks():
	# Bookmarks needs redis storage, if redis is disabled we can't do bookmarks
	if not app.config['REDIS_ENABLED']:
		abort(404)
	if not app.config['BOOKMARKS_ENABLED']:
		abort(404)

	user_bookmarks_key   = 'user:' + session['username'] + ':bookmarks'
	user_bookmark_prefix = 'user:' + session['username'] + ':bookmark:'

	if request.method == 'GET':
		bookmarks = userdata.get_bookmarks()
		return render_template('bookmarks.html', active='user', pwd='', bookmarks=bookmarks)

	elif request.method == 'POST':
		action = request.form['action']

		if action == 'delete':
			bookmark_id     = request.form['bookmark_id']

			if g.redis.exists(user_bookmarks_key):
				if g.redis.sismember(user_bookmarks_key, bookmark_id):

					# Delete from the bookmarks key
					g.redis.srem(user_bookmarks_key, bookmark_id)

					# Delete the bookmark hash
					g.redis.delete(user_bookmark_prefix + bookmark_id)

					# Let the user know and redirect
					flash('Bookmark deleted successfully', 'alert-success')
					return redirect(url_for('bookmarks'))

			flash('Bookmark not found!', 'alert-danger')
			return redirect(url_for('bookmarks'))

		elif action == 'rename':
			bookmark_id     = request.form['bookmark_id']
			bookmark_name   = request.form['bookmark_name']

			if g.redis.exists(user_bookmark_prefix + bookmark_id):
				g.redis.hset(user_bookmark_prefix + bookmark_id, "name", bookmark_name)
				flash('Bookmark renamed successfully', 'alert-success')
				return redirect(url_for('bookmarks'))

			flash('Bookmark not found!', 'alert-danger')
			return redirect(url_for('bookmarks'))


@app.route('/bookmark/<string:bookmark_id>')
@app.login_required
def bookmark(bookmark_id):
	"""This function takes a bookmark ID and redirects the user to the location
	specified by the bookmark in the REDIS database. This only works with
	version 2 bookmarks, not version 1 (Bargate v1.4 or earlier)"""

	if not app.config['REDIS_ENABLED']:
		abort(404)
	if not app.config['BOOKMARKS_ENABLED']:
		abort(404)

	# Prepare the redis key name
	redis_key = 'user:' + session['username'] + ':bookmark:' + bookmark_id

	# bookmarks are a hash with the keys 'version', 'function', 'path' and
	# 'custom_uri' (optional) only proceed if we can find the bmark in redis
	if g.redis.exists(redis_key):
		try:
			# redis returns 'None' for hget if the hash key doesn't exist
			bookmark_version    = g.redis.hget(redis_key, 'version')
			bookmark_function   = g.redis.hget(redis_key, 'function')
			bookmark_path       = g.redis.hget(redis_key, 'path')
			bookmark_custom_uri = g.redis.hget(redis_key, 'custom_uri')
		except Exception as ex:
			app.logger.error('Failed to load v2 bookmark ' + bookmark_id +
				' user: ' + session['username'] + ' error: ' + str(ex))
			abort(404)

		if bookmark_version is None:
			abort(404)

		if bookmark_version != '2':
			abort(404)

		# Handle custom URI bookmarks
		if bookmark_function == 'custom':
			# Set the custom_uri in the session so when the custom function is
			# hit then the user is sent to the right place (maybe)
			session['custom_uri'] = bookmark_custom_uri
			session.modified      = True

			# redirect the user to the custom function
			return redirect(url_for('custom', path=bookmark_path))

		# Handle standard non-custom bookmarks
		else:
			try:
				return redirect(url_for(bookmark_function, path=bookmark_path))
			except werkzeug.routing.BuildError as ex:
				# could not build a URL for that function_name
				# it could be that the function/share was removed by the admin
				# so we should say 404 not found.
				abort(404)

	else:
		abort(404)


@app.route('/online/<last>')
@app.login_required
def online(last=5):
	if not app.config['REDIS_ENABLED']:
		abort(404)

	if not app.config['USER_STATS_ENABLED']:
		abort(404)

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

	usernames = userdata.get_online_users(last)
	return render_template('online.html', online=usernames, active="help", last=last_str)
