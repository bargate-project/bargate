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
from flask import current_app as app

from bargate.lib import userdata


@app.route('/api/init')
@app.set_response_type('json')
def client_init():
	twoStepEnabled = False
	twoStepTrusted = False
	if app.config['TOTP_ENABLED']:
		if app.is_user_logged_in():
			from bargate.lib import totp
			if totp.user_enabled(session['username']):
				twoStepEnabled = True

				if totp.device_trusted(session['username']):
					twoStepTrusted = True

	theme = userdata.get_theme()

	return(jsonify({'code': 0,
		'user': {
			'layout': userdata.get_layout(),
			'token': app.csrfp_token(),
			'theme': theme,
			'theme_classes': userdata.THEMES[theme],
			'hidden': userdata.get_show_hidden_files(),
			'overwrite': userdata.get_overwrite_on_upload(),
			'click': userdata.get_on_file_click(),
			'bmarks': userdata.get_bookmarks(),
			'totp': {
				'enabled': twoStepEnabled,
				'trusted': twoStepTrusted
			},
		},
		'config': {
			'shortname': app.config['APP_DISPLAY_NAME_SHORT'],
			'domain': app.config['SMB_WORKGROUP'],
			'search': app.config['SEARCH_ENABLED'],
			'userdata': app.config['REDIS_ENABLED'],
			'bmark': app.config['BOOKMARKS_ENABLED'],
			'wbinfo': app.config['WBINFO_LOOKUP'],
			'connect': app.config['CONNECT_TO_ENABLED'],
			'totp': {
				'enabled': app.config['TOTP_ENABLED'],
				'ident': app.config['TOTP_IDENT'],
			},
			'themes': userdata.THEMES,
		}}))


@app.route('/api/save', methods=['POST'])
@app.set_response_type('json')
def client_save_setting():
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
		if value not in userdata.THEMES.keys():
			value = app.config['THEME_DEFAULT']

		userdata.save('theme', value)
		return jsonify({'code': 0, 'theme_classes': userdata.THEMES[value]})

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
		return render_template('views/bookmarks.html', active='user', pwd='', bookmarks=bookmarks)

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
