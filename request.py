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

## request.py
# all Flask per-request decorators live here
# to avoid making app.py a very long file
# functions in here register per-request functionality
# with decorators

from flask import Flask, request, session, g, abort
from bargate import app
import bargate.lib.userdata
import bargate.lib.errors
import redis
import time
from random import randint

################################################################################

@app.before_request
def before_request():
	"""This function is run before the request is handled by Flask. At present it checks
	to make sure a valid CSRF token has been supplied if a POST request is made, sets
	the default theme, tells out of date web browsers to foad, and connects to redis
	for user data storage.
	"""

	# Check for MSIE version <= 10
	if (request.user_agent.browser == "msie" and int(round(float(request.user_agent.version))) <= 10):
		return render_template('foad.html')

	## Connect to redis
	if app.config['REDIS_ENABLED']:
		try:
			g.redis = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=0)
			g.redis.get('foo')
		except Exception as ex:
			bargate.lib.errors.fatal('Unable to connect to redis',str(ex))
		
	## Log user last access time
	if 'username' in session:
		bargate.lib.userdata.save('last',str(time.time()))
		bargate.lib.userdata.record_user_activity(session['username'])

################################################################################

@app.context_processor
def context_processor():
	"""This function injects additional variables into Jinja's context"""

	data = {}
	data['bookmarks']   = []
	data['user_theme']  = app.config['THEME_DEFAULT']
	data['user_navbar'] = 'default'

	if app.is_user_logged_in():
		if app.config['REDIS_ENABLED'] and not app.config['DISABLE_APP']:
			data['user_bookmarks'] = bargate.lib.userdata.get_bookmarks()
			data['user_theme']     = bargate.lib.userdata.get_theme()
			data['user_navbar']    = bargate.lib.userdata.get_navbar()	
			data['user_layout']    = bargate.lib.userdata.get_layout()	

	return data

@app.template_global()
def getrandnum():
	return randint(1,app.config['LOGIN_IMAGE_RANDOM_MAX'])
