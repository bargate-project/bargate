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

from flask import session, g, url_for

from bargate import app
from bargate.lib import fs, userdata, errors


@app.before_request
def before_request():
	"""This function is run before the request is handled by Flask. It connects
	connects to REDIS, logs the user access time and asks IE users using version
	10 or lower to upgrade their web browser.
	"""

	# Check bargate started correctly
	if app.error:
		app.logger.error("bargate didn't start correctly: " + app.error)
		return errors.fatalerr("Initialisation error", app.error)

	# Connect to redis
	if app.config['REDIS_ENABLED']:
		try:
			import redis
		except ImportError as ex:
			app.logger.error("bargate didn't start correctly: module 'redis' not installed, but REDIS enabled")
			return errors.fatalerr("Initialisation error",
				"REDIS_ENABLED is set to True, but required module 'redis' is not installed")

		try:
			g.redis = redis.StrictRedis(host=app.config['REDIS_HOST'],
				port=app.config['REDIS_PORT'],
				db=app.config['REDIS_DB'])
			g.redis.get('foo')
		except Exception as ex:
			app.logger.error('Could not connect to REDIS. ' + type(ex).__name__ + ": " + str(ex))
			return errors.fatalerr(ex, 'Could not connect to REDIS. ' + type(ex).__name__ + ": " + str(ex))

		# Log user last access time
		if app.is_user_logged_in():
			userdata.record_user_activity(session['username'])

	# Default to sending HTML responses
	g.response_type = 'html'


@app.context_processor
def context_processor():
	"""This function injects additional variables into Jinja's context"""

	data = {}
	data['bookmarks'] = []
	data['user_theme'] = app.config['THEME_DEFAULT']
	data['theme_classes'] = 'navbar-dark bg-primary'
	data['themes'] = userdata.themes

	if app.is_user_logged_in():
		if app.config['REDIS_ENABLED'] and not app.config['DISABLE_APP']:
			data['user_bookmarks'] = userdata.get_bookmarks()
			data['user_theme'] = userdata.get_theme()
			data['user_layout'] = userdata.get_layout()
			data['theme_classes'] = userdata.themes[data['user_theme']]

	if app.config['LOCAL_FAVICON']:
		data['favicon'] = url_for('local_static', filename='favicon.ico')
	else:
		data['favicon'] = url_for('static', filename='images/favicon.png')

	data['type'] = fs.EntryType

	return data
