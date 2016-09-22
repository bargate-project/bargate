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

from flask import Flask, request, session, g, abort, render_template, url_for
from bargate import app
import bargate.lib.userdata
import bargate.lib.errors
import redis
import time

################################################################################

@app.before_request
def before_request():
	"""This function is run before the request is handled by Flask. It connects 
	connects to REDIS, logs the user access time and asks IE users using version
	10 or lower to upgrade their web browser.
	"""

	# Check bargate started correctly
	if app.error:
		return bargate.lib.errors.fatalerr(message=app.error)		

	# Check for MSIE version <= 10
	if (request.user_agent.browser == "msie" and int(round(float(request.user_agent.version))) <= 10):
		return render_template('foad.html')

	## Connect to redis
	if app.config['REDIS_ENABLED']:
		try:
			g.redis = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=0)
			g.redis.get('foo')
		except Exception as ex:
			return bargate.lib.errors.fatalerr(message='Bargate could not connect to the REDIS server',debug=str(ex))
			
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

	## The favicon
	if app.config['LOCAL_FAVICON']:
		data['favicon'] = url_for('local_static', filename='favicon.ico')
	else:
		data['favicon'] = url_for('static', filename='favicon.ico')

	return data

