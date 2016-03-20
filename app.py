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

from flask import Flask, request, session, g, abort, flash, redirect, url_for
from ConfigParser import RawConfigParser
import jinja2 
import logging
import os
import os.path
import binascii
from logging.handlers import SMTPHandler
from logging.handlers import RotatingFileHandler
from logging import Formatter
from functools import wraps   ## used for login_required and downtime_check

class Bargate(Flask):

	class CsrfpException(Exception):
		pass

	def __init__(self, init_object_name):
		super(Bargate, self).__init__(init_object_name)

		self._init_config()
		self._init_logging()
		self._init_templates()
		self._init_debug()
		self._init_csrfp()

		## Get the sections of the shares config file
		self.sharesConfig = RawConfigParser()
		with open(self.config['SHARES_CONFIG'], 'r') as f:
			self.sharesConfig.readfp(f)
		self.sharesList = self.sharesConfig.sections()

		## Modal errors
		self.add_template_global(self.get_modal_error)

################################################################################

	def _init_config(self):
		## Load the default config
		self.config.from_object("bargate.defaultcfg")

		# try to load config from various paths
		if os.path.isfile('/etc/bargate.conf'):
			self.config.from_pyfile('/etc/bargate.conf')
		elif os.path.isfile('/etc/bargate/bargate.conf'):
			self.config.from_pyfile('/etc/bargate/bargate.conf')
		elif os.path.isfile('/data/bargate/bargate.conf'):
			self.config.from_pyfile('/data/bargate/bargate.conf')
		elif os.path.isfile('/data/fwa/bargate.conf'):
			self.config.from_pyfile('/data/fwa/bargate.conf')

################################################################################

	def _init_logging(self):

		## Set up logging to file
		if self.config['FILE_LOG'] == True:
			self.file_handler = RotatingFileHandler(self.config['LOG_DIR'] + '/' + self.config['LOG_FILE'], 'a', self.config['LOG_FILE_MAX_SIZE'], self.config['LOG_FILE_MAX_FILES'])
			self.file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
			self.logger.addHandler(self.file_handler)

		## Set the log level based on debug flag
		if self.debug:
			self.logger.setLevel(logging.DEBUG)
			self.file_handler.setLevel(logging.DEBUG)
		else:
			self.logger.setLevel(logging.INFO)
			self.file_handler.setLevel(logging.INFO)

		## Output some startup info
		self.logger.info('bargate version ' + self.config['VERSION'] + ' starting')
		if self.debug:
			self.logger.info('bargate is running in DEBUG mode')

		## Log if the app is disabled at startup
		if self.config['DISABLE_APP']:
			self.logger.info('bargate is running in DISABLED mode')

		# set up e-mail alert logging
		if self.config['EMAIL_ALERTS'] == True:
			## Log to file where e-mail alerts are going to
			self.logger.info('fatal errors will generate e-mail alerts and will be sent to: ' + str(self.config['ADMINS']))

			## Create the mail handler
			smtp_handler = SMTPHandler(self.config['SMTP_SERVER'], self.config['EMAIL_FROM'], self.config['ADMINS'], self.config['EMAIL_SUBJECT'])

			## Set the minimum log level (errors) and set a formatter
			smtp_handler.setLevel(logging.ERROR)
			smtp_handler.setFormatter(Formatter("""A fatal error occured in Bargate.

Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Function:           %(funcName)s
Time:               %(asctime)s
Logger Name:        %(name)s
Process ID:         %(process)d

Further Details:

%(message)s

"""))

			self.logger.addHandler(smtp_handler)

################################################################################

	def _init_templates(self):
		# load user defined templates
		if self.config['LOCAL_TEMPLATE_DIR']:

			if os.path.isdir(self.config['LOCAL_TEMPLATE_DIR']):

				self.jinja_loader = jinja2.ChoiceLoader(
				[
					jinja2.FileSystemLoader(self.config['LOCAL_TEMPLATE_DIR']),
					self.jinja_loader,
				])

				self.logger.info('site-specific templates will be loaded from: ' + str(self.config['LOCAL_TEMPLATE_DIR']))

			else:
				self.logger.error('site-specific templates cannot be loaded because LOCAL_TEMPLATE_DIR is not a directory')

################################################################################

	def _init_debug(self):
		if self.config['DEBUG_TOOLBAR']:
			self.debug = True
			from flask_debugtoolbar import DebugToolbarExtension
			toolbar = DebugToolbarExtension(self)
			self.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
			self.logger.info('debug toolbar enabled - DO NOT USE THIS ON PRODUCTION SYSTEMS!')

################################################################################

	def _init_csrfp(self):
		self._exempt_views = set()
		self.add_template_global(self.csrfp_token)
		self.before_request(self.csrfp_before_request)

################################################################################
## User session/login functions

	def login_required(self,f):
		"""This is a decorator function that when called ensures the user has logged in.
		Usage is as such: @app.login_required
		"""
		@wraps(f)
		def decorated_function(*args, **kwargs):

			if not self.is_user_logged_in():
				flash('You must be logged in to do that','alert-danger')
				session['next'] = request.url ## store the current url we're on
				return redirect(url_for('login'))

			return f(*args, **kwargs)
		return decorated_function

	def is_user_logged_in(self):
		return session.get('logged_in',False)

################################################################################

	def allow_disable(self,f):
		"""This is a decorator function that when called disables the view if the application
		is currently disabled. This allows selective disabling of parts of the application.
		Usage is as such: @app.allow_disable
		"""
		@wraps(f)
		def decorated_function(*args, **kwargs):
			if self.config['DISABLE_APP']:
				flash('Service Temporarily Unavailable - Normal service will be restored as soon as possible.','alert-warning')
				bgnumber = randint(1,2)
				return render_template('login.html', bgnumber=bgnumber)
			return f(*args, **kwargs)
		return decorated_function

################################################################################

	## CSRF Protection (csrfp) functionality

	def csrf_token(self):
		return self.csrfp_token()

	def csrfp_token(self):
		if '_csrfp_token' not in session:
			session['_csrfp_token'] = self.token()
		return session['_csrfp_token']

	def csrfp_before_request(self):
		"""Performs the checking of CSRF tokens. This check is skipped for the 
		GET, HEAD, OPTIONS and TRACE methods within HTTP, and is also skipped
		for any function that has been added to _exempt_views by use of the
		disable_csrf_check decorator."""

		# For methods that require CSRF checking
		if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
			# Get the function that is rendering the current view
			view = self.view_functions.get(request.endpoint)
			view_location = view.__module__ + '.' + view.__name__

			# If the view is not exempt
			if not view_location in self._exempt_views:
				token = session.get('_csrfp_token')

				if not token or token != request.form.get('_csrfp_token'):
					if 'username' in session:
						self.logger.warning('CSRF Protection alert: %s failed to present a valid POST token', session['username'])
					else:
			 			self.logger.warning('CSRF Protection alert: a non-logged in user failed to present a valid POST token')

					# The user should not have accidentally triggered this
					raise self.CsrfpException()

			else:
				self.logger.debug('View ' + view_location + ' is exempt from CSRF Protection')

################################################################################

	def csrfp_exempt(self, view):
		"""A decorator that can be used to exclude a view from CSRF validation.
		Example usage of disable_csrf_check might look something like this:
			@app.disable_csrf_check
			@app.route('/some_view')
			def some_view():
				return render_template('some_view.html')
		:param view: The view to be wrapped by the decorator.
		"""

		view_location = view.__module__ + '.' + view.__name__
		self._exempt_views.add(view_location)
		self.logger.debug('Added CSRF Protection exemption for ' + view_location)
		return view

################################################################################

	def token(self,bytes=64):
		"""Generates a random token. This code was derived from the
			proposed new 'token' functions in Python 3.6, see:
			https://bitbucket.org/sdaprano/secrets/"""

		return binascii.hexlify(os.urandom(bytes))

################################################################################

	def get_modal_error(self):
		"""This function clears any currently set error popup. It is only to be
		called from inside a jinja template
		"""

		title   = session['modal_error_title']
		message = session['modal_error_message']

		## clear the session
		session['modal_error']         = False
		session['modal_error_title']   = ""
		session['modal_error_message'] = ""
	
		return (title,message)

	def set_modal_error(title,message):
		"""This function will create and show a
		popup dialog error on the next time a page
		is loaded. Use this before running a redirect.
		"""

		session['modal_error']         = True
		session['modal_error_title']   = title
		session['modal_error_message'] = message

################################################################################

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

