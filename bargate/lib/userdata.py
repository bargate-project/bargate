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
from bargate import app
from flask import Flask, request, session, redirect, url_for, flash, g, abort, render_template
import mimetypes
import os
from random import randint
import time
import json
import werkzeug

################################################################################

def record_user_activity(user_id,expire_minutes=1440):
	if app.config['REDIS_ENABLED']:
		now = int(time.time())
		expires = now + (expire_minutes * 60) + 10

		all_users_key = 'online-users/%d' % (now // 60)
		user_key = 'user-activity/%s' % user_id
		p = g.redis.pipeline()
		p.sadd(all_users_key, user_id)
		p.set(user_key, now)
		p.expireat(all_users_key, expires)
		p.expireat(user_key, expires)
		p.execute()

################################################################################

def save(key,value):
	if app.config['REDIS_ENABLED']:
		g.redis.set('user:' + session['username'] + ':' + key,value)

################################################################################

def get_bookmarks():
	user_bookmarks_key = 'user:' + session['username'] + ':bookmarks'
	user_bookmark_key  = 'user:' + session['username'] + ':bookmark:'
	bookmarks          = list()

	if app.config['REDIS_ENABLED'] and 'redis' in g:	
		if g.redis.exists(user_bookmarks_key):
			try:
				user_bookmarks = g.redis.smembers(user_bookmarks_key)
			except Exception as ex:	
				app.logger.error('Failed to load bookmarks for ' + session['username'] + ': ' + str(ex))
				return bookmarks_list

			if user_bookmarks != None:
				if isinstance(user_bookmarks,set):
					for bookmark_id in user_bookmarks:

						try:
							bookmark = g.redis.hgetall(user_bookmark_key + bookmark_id)
						except Exception as ex:
							app.logger.error('Failed to load bookmark ' + bookmark_id + ' for ' + session['username'] + ': ' + str(ex))
							continue

						if 'version' not in bookmark:
							## Version 1 bookmark - we link directly from here
							if 'function' not in bookmark or 'path' not in bookmark:
								app.logger.error('Failed to load bookmark ' + bookmark_id + ' for ' + session['username'] + ': ', 'function and/or path was not set')
								continue
		
							try:
								bookmark['url'] = url_for(bookmark['function'],path=bookmark['path'])
							except werkzeug.routing.BuildError as ex:
								app.logger.error('Failed to load bookmark ' + bookmark_name + ' for ' + session['username'] + ': Invalid bookmark function: ', str(ex))
								continue

							## Version 1 bookmarks stored the name of the bookmark as the ID :(
							bookmark['name'] = bookmark_id

						else:
							if bookmark['version'] == '2':
								## Version 2 bookmark - use a resolver / redirector function
								if 'name' not in bookmark:
									app.logger.error('Failed to load bookmark ' + bookmark_id + ' for ' + session['username'] + ': No name set')
									continue

								bookmark['url'] = url_for('bookmark',bookmark_id=bookmark_id)
							else:
								app.logger.error('Failed to load bookmark ' + bookmark_id + ' for ' + session['username'] + ': Invalid value for version field')
								continue

						bookmark['id'] = bookmark_id
						bookmarks.append(bookmark)

				else:
					app.logger.error('Failed to load bookmarks','Invalid redis data type when loading bookmarks set for ' + session['username'])
			
	return bookmarks

################################################################################

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

	## If we didn't return a new theme, return the default from the config file
	return app.config['LAYOUT_DEFAULT']

################################################################################

def get_theme():
	if 'redis' in g:
		try:
			theme = g.redis.get('user:' + session['username'] + ':theme')
			if theme != None:
				return theme
		
		except Exception as ex:
			app.logger.error('An error occured whilst loading data from redis: ' + str(ex))

	## If we didn't return a new theme, return the default from the config file
	return app.config['THEME_DEFAULT']

################################################################################

def get_navbar():
	if 'redis' in g:
		try:
			navbar = g.redis.get('user:' + session['username'] + ':navbar_alt')
			if navbar != None:
				return navbar
				
		except Exception as ex:
			app.logger.error('An error occured whilst loading data from redis: ' + str(ex))

	return 'default'

################################################################################

def get_show_hidden_files():
	if 'username' in session:
	
		## Get a cached response rather than asking REDIS every time
		hidden_files = g.get('hidden_files', None)
		if not hidden_files == None:
			return hidden_files
		else:
			if app.config['REDIS_ENABLED']:
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

def get_overwrite_on_upload():
	if 'username' in session:
		if app.config['REDIS_ENABLED']:
			try:
				overwrite_on_upload = g.redis.get('user:' + session['username'] + ':upload_overwrite')

				if overwrite_on_upload != None:
					if overwrite_on_upload == 'yes':
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
			if app.config['REDIS_ENABLED']:
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

def get_online_users(minutes=15):
	if app.config['REDIS_ENABLED']:
		if minutes > 86400:
		    minutes = 86400
		current = int(time.time()) // 60
		minutes = xrange(minutes)
		return g.redis.sunion(['online-users/%d' % (current - x) for x in minutes])
	else:
		return []

