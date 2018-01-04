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

from flask import session, render_template

from bargate import app
from bargate.lib.errors import stderr
from bargate.lib.core import check_path


class LibraryBase:
	# def decode_exception(self, ex)
	# def smb_auth(self, user, pass)

	def return_exception(self, ex):
		app.logger.debug("smblib.return_exception: called with '" + str(ex))
		app.logger.debug(traceback.format_exc())
		(title, desc) = self.decode_exception(ex)
		app.logger.debug("smblib.return_exception: decoded to: '" + title + "', '" + desc + "'")
		return stderr(title, desc)

	def smb_connection_init(self, endpoint_name, action, path):
		app.logger.debug("smb_connection_init('" + endpoint_name + "','" + action + "','" + path + "')")

		self.endpoint_name = endpoint_name
		self.action = action
		self.path = path

		if self.endpoint_name == 'custom':
			self.endpoint_path = unicode(session['custom_uri'])
			self.endpoint_url  = '/c'
			self.endpoint_title = unicode(session['custom_uri'])
			self.active = 'custom'

		else:
			if not app.sharesConfig.has_section(self.endpoint_name):
				return stderr('Not found', 'The endpoint specified was not found')

			if app.sharesConfig.has_option(self.endpoint_name, 'path'):
				self.endpoint_path = app.sharesConfig.get(self.endpoint_name, 'path')
			else:
				return stderr('Invalid configuration', "'path' is not set on endpoint '" + self.endpoint_name + "'")

			if app.sharesConfig.has_option(self.endpoint_name, 'url'):
				self.endpoint_url = app.sharesConfig.get(self.endpoint_name, 'url')
			else:
				self.endpoint_url = '/' + self.endpoint_name

			self.endpoint_path = self.endpoint_path.replace("%USERNAME%", session['username'])
			self.endpoint_path = self.endpoint_path.replace("%USER%", session['username'])

			if app.config['LDAP_HOMEDIR']:
				if 'ldap_homedir' in session:
					if session['ldap_homedir'] is not None:
						self.endpoint_path = self.endpoint_path.replace("%LDAP_HOMEDIR%", session['ldap_homedir'])

			if app.sharesConfig.has_option(self.endpoint_name, 'display'):
				self.endpoint_title = app.sharesConfig.get(self.endpoint_name, 'display')
			else:
				self.endpoint_title = self.endpoint_name

			if app.sharesConfig.has_option(self.endpoint_name, 'menu'):
				self.active = app.sharesConfig.get(self.endpoint_name, 'menu')
			else:
				self.active = self.endpoint_name

		# Check the path is valid
		try:
			check_path(self.path)
		except ValueError:
			return stderr('Invalid path', 'You tried to navigate to a name of a file or diretory which is invalid')

		# Work out the 'entry name'
		if len(self.path) > 0:
			(a, b, self.entry_name) = self.path.rpartition('/')
		else:
			self.entry_name = u''

		# the address should always start with smb://, we don't support anything else.
		if not self.endpoint_path.startswith("smb://"):
			return stderr('Configuration error', 'The server URL must start with smb://')

		app.logger.debug("Connection preperation complete")

	def action_dispatch(self):
		app.logger.debug("smblib.action_dispatch: Going to call: _action_" + self.action)

		try:
			method = getattr(self, '_action_' + self.action)
		except AttributeError:
			return stderr('Not found', 'The action specified was not found')

		return method()

	def _action_browse(self):
		app.logger.debug("_action_browse()")

		return render_template('browse.html',
			active=self.endpoint_name,
			browse_mode=True,
			epname=self.endpoint_name,
			epurl=self.endpoint_url,
			path=self.path)

	def _action_view(self):
		app.logger.debug("_action_view()")

		return self._action_download(view=True)
