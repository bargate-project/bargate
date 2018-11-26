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

import uuid

from flask import session, g
from flask import current_app as app


THEMES = {'cerulean': ['navbar-dark', 'bg-primary'],
	'cosmo': ['navbar-dark', 'bg-dark'],
	'flatly': ['navbar-dark', 'bg-primary'],
	'litera': ['navbar-light', 'bg-light'],
	'lumen': ['navbar-dark', 'bg-primary'],
	'lux': ['navbar-dark', 'bg-dark'],
	'materia': ['navbar-dark', 'bg-primary'],
	'pulse': ['navbar-dark', 'bg-primary'],
	'strap': ['navbar-dark', 'bg-primary'],
	'yeti': ['navbar-dark', 'bg-dark']}


def save(key, value):
	if app.config['REDIS_ENABLED']:
		g.redis.set('user:' + session['username'] + ':' + key, value)


def get_layout():
	if 'redis' in g:
		try:
			layout = g.redis.get('user:' + session['username'] + ':layout')
			if layout == 'grid':
				return 'grid'
			elif layout == 'list':
				return 'list'
			else:
				return app.config['LAYOUT_DEFAULT']

		except Exception as ex:
			app.logger.error('An error occured whilst loading data from redis: ' + str(ex))

	# If we didn't return a new theme, return the default from the config file
	return app.config['LAYOUT_DEFAULT']


def get_theme():
	if 'redis' in g:
		try:
			theme = g.redis.get('user:' + session['username'] + ':theme')
			if theme is not None:
				if theme in THEMES.keys():
					return theme

		except Exception as ex:
			app.logger.error('An error occured whilst loading data from redis: ' + str(ex))

	if app.config['THEME_DEFAULT'] not in THEMES.keys():
		return 'cosmo'
	else:
		return app.config['THEME_DEFAULT']


def get_show_hidden_files():
	if app.is_user_logged_in():

		# Get a cached response rather than asking REDIS every time
		hidden_files = g.get('hidden_files', None)
		if hidden_files is not None:
			return hidden_files
		else:
			if app.config['REDIS_ENABLED']:
				try:
					hidden_files = g.redis.get('user:' + session['username'] + ':hidden_files')

					if hidden_files is not None:
						if hidden_files == 'show':
							g.hidden_files = True
							return True

				except Exception as ex:
					app.logger.error('Unable to speak to redis: ' + str(ex))

	g.hidden_files = False
	return False


def get_overwrite_on_upload():
	if app.is_user_logged_in():
		if app.config['REDIS_ENABLED']:
			try:
				overwrite_on_upload = g.redis.get('user:' + session['username'] + ':upload_overwrite')

				if overwrite_on_upload is not None:
					if overwrite_on_upload == 'yes':
						return True

			except Exception as ex:
				app.logger.error('Unable to speak to redis: ' + str(ex))

	return False


def get_on_file_click():
	if app.is_user_logged_in():

		# Get a cached response rather than asking REDIS every time
		on_file_click = g.get('on_file_click', None)
		if on_file_click is not None:
			return on_file_click
		else:
			if app.config['REDIS_ENABLED']:
				try:
					on_file_click = g.redis.get('user:' + session['username'] + ':on_file_click')

					if on_file_click is not None:
						g.on_file_click = on_file_click
						return on_file_click
					else:
						g.on_file_click = 'ask'
						return 'ask'

				except Exception as ex:
					app.logger.error('Unable to speak to redis: ' + str(ex))

	g.on_file_click = 'ask'
	return 'ask'


def save_bookmark(bookmark_name, endpoint, path):
	# Generate a unique identifier for this bookmark
	bookmark_id = uuid.uuid4().hex

	# Turn this into a redis key for the new bookmark
	redis_key = 'user:' + session['username'] + ':bookmark:' + bookmark_id

	# Store all the details of this bookmark in REDIS
	g.redis.hset(redis_key, 'version', '2')
	g.redis.hset(redis_key, 'function', endpoint)
	g.redis.hset(redis_key, 'path', path)
	g.redis.hset(redis_key, 'name', bookmark_name)

	# if we're on a custom server then we need to store the URL
	# to that server otherwise the bookmark is useless.
	if endpoint == 'custom':
		g.redis.hset(redis_key, 'custom_uri', session['custom_uri'])

	# add the new bookmark name to the list of bookmarks for the user
	g.redis.sadd('user:' + session['username'] + ':bookmarks', bookmark_id)

	return {'id': bookmark_id, 'epname': endpoint, 'name': bookmark_name, 'path': path}


def get_bookmarks():
	bookmarks = []

	if app.is_user_logged_in and app.config['BOOKMARKS_ENABLED'] and app.config['REDIS_ENABLED']:
		user_bookmarks_key = 'user:' + session['username'] + ':bookmarks'
		user_bookmark_key  = 'user:' + session['username'] + ':bookmark:'

		if g.redis.exists(user_bookmarks_key):
			try:
				user_bookmarks = g.redis.smembers(user_bookmarks_key)
			except Exception as ex:
				app.logger.error('Failed to load bookmarks for ' + session['username'] + ': ' + str(ex))
				return []

			if user_bookmarks is not None:
				if isinstance(user_bookmarks, set):
					for bid in user_bookmarks:

						try:
							bmark = g.redis.hgetall(user_bookmark_key + bid)

							if 'version' not in bmark:
								continue

							# Make sure the function/epname still exists and is loaded
							if app.sharesConfig.has_section(bmark['function']):
								if app.sharesConfig.has_option(bmark['function'], 'display'):
									eptitle = app.sharesConfig.get(bmark['function'], 'display')
								else:
									eptitle = app.sharesConfig.get(bmark['function'], 'url')
							else:
								continue

							bookmarks.append({'id': bid,
								'name': bmark['name'],
								'path': bmark['path'],
								'epname': bmark['function'],
								'eptitle': eptitle})

						except Exception as ex:
							app.logger.error('Failed to load bookmark ' + bid + ' for ' +
								session['username'] + ': ' + type(ex).__name__ + " - " + str(ex))
							continue
				else:
					app.logger.error('Failed to load bookmarks',
						'Invalid redis data type when loading bookmarks set for ' + session['username'])

	return bookmarks
