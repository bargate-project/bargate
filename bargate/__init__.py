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

# start Bargate
from bargate.app import Bargate
app = Bargate(__name__)

# only continue if bargate started successfully
if not app.error:
	# process per-request decorators
	import bargate.request

	# process view functions decorators
	import bargate.views.main
	import bargate.views.userdata
	import bargate.views.errors
	import bargate.views.smb

	# optionally load TOTP support
	if app.config['TOTP_ENABLED']:
		if app.config['REDIS_ENABLED']:
			import bargate.views.totp
		else:
			app.logger.warn("Cannot enable TOTP 2-factor auth because REDIS is not enabled")

	# add url rules for the shares/functions defined in shares.conf
	for section in app.sharesList:
		try:
			url = app.sharesConfig.get(section,'url')
			if not url.startswith('/'):
				url = "/" + url

			# If the user goes to /endpoint or /endpoint/ - .e.g the default for GET, and all POST requests (action and path are sent as form variables in POSTS)
			app.add_url_rule(url,endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'], defaults={'path': '', 'action': 'browse'})
			app.add_url_rule(url + '/',endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'], defaults={'path': '', 'action': 'browse'})

			# If the user goes to /endpoint/action or /endpoint/action/
			app.add_url_rule(url + '/<string:action>',endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'], defaults={'path': ''})
			app.add_url_rule(url + '/<string:action>/',endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'], defaults={'path': ''})

			# If the user goes to /endpoint/browse/path/
			# this is needed such that the default action is browse
			# otherwise we can't build url_for urls e.g. url_for('personal',path='mydocuments')
			app.add_url_rule(url + '/browse/<path:path>',endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'], defaults={'action': 'browse'})
			app.add_url_rule(url + '/browse/<path:path>/',endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'], defaults={'action': 'browse'})

			# If the user goes to /endpoint/action/path/
			app.add_url_rule(url + '/<string:action>/<path:path>',endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'])
			app.add_url_rule(url + '/<string:action>/<path:path>/',endpoint=section,view_func=bargate.views.smb.share_handler,methods=['GET','POST'])

			app.logger.debug("Created share entry '" + section + "' available at " + url)

		except Exception as ex:
			app.logger.error("Could not create file share '" + section + "':" + str(type(ex)) + ":" + str(ex))
