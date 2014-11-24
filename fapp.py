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

from flask import Flask, request, session
from ConfigParser import RawConfigParser
import jinja2 

class BargateFlask(Flask):
	sharesConfig = RawConfigParser()

	def load_user_templates(self):
		if self.config['LOCAL_TEMPLATE_DIR']:
			choice_loader = jinja2.ChoiceLoader(
			[
				jinja2.FileSystemLoader(self.config['LOCAL_TEMPLATE_DIR']),
				self.jinja_loader,
			])
			self.jinja_loader = choice_loader
			self.logger.info('bargate will load templates from local source: ' + str(self.config['LOCAL_TEMPLATE_DIR']))
	
	def load_share_config(self):
		with open(self.config['SHARES_CONFIG'], 'r') as f:
			self.sharesConfig.readfp(f)

	def log_exception(self, exc_info):
		"""Logs an exception.  This is called by :meth:`handle_exception`
		if debugging is disabled and right before the handler is called.
		This implementation logs the exception as an error on the
		:attr:`logger` but sends extra information such as the remote IP
		address, the username, etc. This extends the default implementation
		in Flask.

		.. versionadded:: 0.8
		"""

		if 'username' in session:
			usr = session['username']
		else:
			usr = 'Not logged in'

		self.logger.error("""Path:                 %s 
HTTP Method:          %s
Client IP Address:    %s
User Agent:           %s
User Platform:        %s
User Browser:         %s
User Browser Version: %s
Username:             %s
""" % (
			request.path,
			request.method,
			request.remote_addr,
			request.user_agent.string,
			request.user_agent.platform,
			request.user_agent.browser,
			request.user_agent.version,
			usr,
			
		), exc_info=exc_info)

