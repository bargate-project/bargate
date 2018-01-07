#!/usr/bin/python2
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

import traceback

from bargate.app import Bargate

app = Bargate(__name__)

# Load the SMB library
try:
	if app.config['SMB_LIBRARY'] == "pysmbc":
		# libsmbclient backend
		from bargate.smb.pysmbc import BargateSMBLibrary
	elif app.config['SMB_LIBRARY'] == "pysmb":
		# pure python pysmb backend
		from bargate.smb.pysmb import BargateSMBLibrary
	else:
		raise Exception("SMB_LIBRARY is set to an unknown library")

	app.set_smb_library(BargateSMBLibrary())
except Exception as ex:
	app.logger.error("Could not load the SMB library: " + str(type(ex)) + " " + str(ex))
	app.logger.error(traceback.format_exc())
	app.error = "Could not load the SMB library: " + str(type(ex)) + " " + str(ex)

# process per-request decorators
from bargate import request # noqa

# process view functions decorators
from bargate.views import main, userdata, errors, smb # noqa

# optionally load TOTP support
if app.config['TOTP_ENABLED']:
	if app.config['REDIS_ENABLED']:
		from bargate.views import totp # noqa
	else:
		app.error = "Cannot enable TOTP 2-factor auth because REDIS is not enabled"

if not app.error:
	# add url rules for the shares/endpoints
	for section in app.sharesList:
		if section == 'custom':
			app.logger.error("Could not create endpoint 'custom': name is reserved")
			continue

		if not app.sharesConfig.has_option(section, 'url'):
			url = '/' + section
		else:
			url = app.sharesConfig.get(section, 'url')

			if not url.startswith('/'):
				url = "/" + url

		if not app.sharesConfig.has_option(section, 'path'):
			app.logger.error("Could not create endpoint '" + section + "': parameter 'path' is not set")
			continue

		try:
			# If the user goes to /endpoint/browse/ or /endpoint/browse
			app.add_url_rule(url + '/browse/', endpoint=section,
								view_func=smb.endpoint_handler,
								defaults={'action': 'browse', 'path': ''})

			app.add_url_rule(url + '/browse',
								endpoint=section,
								view_func=smb.endpoint_handler,
								defaults={'action': 'browse', 'path': ''})

			# If the user goes to /endpoint or /endpoint/
			app.add_url_rule(url,
								endpoint=section,
								view_func=smb.endpoint_handler,
								defaults={'path': '', 'action': 'browse'})

			app.add_url_rule(url + '/',
								endpoint=section,
								view_func=smb.endpoint_handler,
								defaults={'path': '', 'action': 'browse'})

			# If the user goes to /endpoint/browse/path/
			app.add_url_rule(url + '/browse/<path:path>',
								endpoint=section,
								view_func=smb.endpoint_handler,
								defaults={'action': 'browse'})

			app.add_url_rule(url + '/browse/<path:path>/',
								endpoint=section,
								view_func=smb.endpoint_handler,
								defaults={'action': 'browse'})

			# If the user goes to /endpoint/<action>/path/
			app.add_url_rule(url + '/<string:action>/<path:path>',
								endpoint=section,
								view_func=smb.endpoint_handler)

			app.add_url_rule(url + '/<string:action>/<path:path>/', endpoint=section, view_func=smb.endpoint_handler)

			app.logger.debug("Created endpoint named '" + section + "' available at " + url)

		except Exception as ex:
			app.logger.error("Could not create file share '" + section + "': " + str(ex))
