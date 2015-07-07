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

from flask import Flask
import logging
import os.path
from logging.handlers import SMTPHandler
from logging.handlers import RotatingFileHandler
from logging import Formatter
from bargate.fapp import BargateFlask
from datetime import timedelta
from ConfigParser import RawConfigParser

################################################################################
#### Default config options

## Debug mode. This engages the web-based debug mode
DEBUG = False

## Enable the debug toolbar. DO NOT DO THIS ON A PRODUCTION SYSTEM. EVER. It exposes SECRET_KEY and ENCRYPT_KEY.
DEBUG_TOOLBAR = False

## Many errors don't show a full stack trace as they show a redirected 'error popup'. Set this to True to disable that behaviour and show full errors.
DEBUG_FULL_ERRORS = True

## Session signing key
# Key used to sign/encrypt session data stored in cookies.
# If you've set up bargate behind a load balancer then this must match on all
# web servers.
SECRET_KEY = ''

## Secret password encryption key
# MUST BE EXACTLY 32 CHARACTERS LONG
# If you've set up bargate behind a load balancer then this must match on all
# web servers.
ENCRYPT_KEY = ''

## The 'workgroup' that SMBC should use for auth
SMB_WORKGROUP = 'MSHOME'

## Maximum file upload size
# 256MB by default
MAX_CONTENT_LENGTH = 256 * 1024 * 1024

## File 'types' we don't allow people to upload
BANNED_EXTENSIONS = set([
"ade", "adp", "bat", "chm", "cmd", "com", "cpl", "exe",
"hta", "ins", "isp", "jse", "lib", "mde", "msc", "msp",
"mst", "pif", "scr", "sct", "shb", "sys", "vb", "vbe",
"vbs", "vxd", "wsc", "wsf", "wsh"
])

## File logging
FILE_LOG=True
LOG_FILE='bargate.log'
LOG_DIR='/tmp'
LOG_FILE_MAX_SIZE=1 * 1024 * 1024
LOG_FILE_MAX_FILES=10

EMAIL_ALERTS=False
ADMINS=['root']
SMTP_SERVER='localhost'
EMAIL_FROM='root'
EMAIL_SUBJECT='Bargate Runtime Error'

## Redis
REDIS_ENABLED=True
REDIS_HOST='localhost'
REDIS_PORT=6379

## Disable the application or not
# Default to true if no config file to make sure a config file has been found.
DISABLE_APP=True

## Default bootstrap/bootswatch theme
THEME_DEFAULT='lumen'

## Bargate internal version number
VERSION='1.1'

## Flask defaults (change to what we prefer)
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
PREFERRED_URL_SCHEME='https'
USE_X_SENDFILE=False
PERMANENT_SESSION_LIFETIME=timedelta(days=7)

## Shares config file
SHARES_CONFIG='/data/fwa/shares.conf'
SHARES_DEFAULT='personal'

## Local templates to override built in ones
LOCAL_TEMPLATE_DIR=False

# Name of the app to display everywhere
APP_DISPLAY_NAME='Filestore Web Access'
APP_DISPLAY_NAME_SHORT='FWA'

## Default to LDAP auth - PLEASE DO NOT USE KERBEROS unless you don't have LDAP (?!?!)
AUTH_TYPE='ldap'

## LDAP
LDAP_URI='ldaps://localhost.localdomain'
LDAP_SEARCH_BASE=''
LDAP_USER_ATTRIBUTE='sAMAccountName' ## default to AD style as lets face it, sadly, most people use i
LDAP_ANON_BIND=True
LDAP_BIND_USER=''
LDAP_BIND_PW=''

## LDAP homedir attribute support
# You MUST use AUTH_TYPE 'ldap' or this setting will be ignored
LDAP_HOMEDIR=False
LDAP_HOME_ATTRIBUTE='homeDirectory' ## default to AD style as lets face it, sadly, most people use it
LDAP_HOMEDIR_IS_UNC=True

## Kerberos configuration
KRB5_SERVICE = 'krbtgt/localdomain'
KRB5_DOMAIN  = 'localhost.localdomain'

################################################################################

# set up our application
app = BargateFlask(__name__)

# load default config
app.config.from_object(__name__)

# try to load config from various paths
if os.path.isfile('/etc/bargate.conf'):
	app.config.from_pyfile('/etc/bargate.conf')
elif os.path.isfile('/etc/bargate/bargate.conf'):
	app.config.from_pyfile('/etc/bargate/bargate.conf')
elif os.path.isfile('/data/fwa/bargate.conf'):
	app.config.from_pyfile('/data/fwa/bargate.conf')
elif os.path.isfile('/data/bargate/bargate.conf'):
	app.config.from_pyfile('/data/bargate/bargate.conf')

## Set up logging to file
if app.config['FILE_LOG'] == True:
	file_handler = RotatingFileHandler(app.config['LOG_DIR'] + '/' + app.config['LOG_FILE'], 'a', app.config['LOG_FILE_MAX_SIZE'], app.config['LOG_FILE_MAX_FILES'])
	file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
	app.logger.addHandler(file_handler)

## Set up the max log level
if app.debug:
	app.logger.setLevel(logging.DEBUG)
	file_handler.setLevel(logging.DEBUG)
else:
	app.logger.setLevel(logging.INFO)
	file_handler.setLevel(logging.INFO)

# load user defined templates
app.load_user_templates()

## Output some startup info
app.logger.info('bargate version ' + app.config['VERSION'] + ' initialised')
app.logger.info('bargate debug status: ' + str(app.config['DEBUG']))

## Log if the app is disabled at startup
if app.config['DISABLE_APP']:
	app.logger.info('bargate is currently disabled')

# set up e-mail alert logging
if app.config['EMAIL_ALERTS'] == True:
	## Log to file where e-mail alerts are going to
	app.logger.info('bargate e-mail alerts are enabled and being sent to: ' + str(app.config['ADMINS']))

	## Create the mail handler
	mail_handler = SMTPHandler(app.config['SMTP_SERVER'], app.config['EMAIL_FROM'], app.config['ADMINS'], app.config['EMAIL_SUBJECT'])

	## Set the minimum log level (errors) and set a formatter
	mail_handler.setLevel(logging.ERROR)
	mail_handler.setFormatter(Formatter("""
A fatal error occured in Bargate.

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

	app.logger.addHandler(mail_handler)

## Debug Toolbar
if app.config['DEBUG_TOOLBAR']:
	app.debug = True
	from flask_debugtoolbar import DebugToolbarExtension
	toolbar = DebugToolbarExtension(app)
	app.logger.info('bargate debug toolbar enabled')

# load core functions
import bargate.core

# import modules
import bargate.smb
import bargate.errors
import bargate.views
import bargate.smb_views
import bargate.mime
import bargate.settings

# load anti csrf function reference into template engine
app.jinja_env.globals['csrf_token']      = core.generate_csrf_token
app.jinja_env.globals['get_user_theme']  = settings.get_user_theme
app.jinja_env.globals['get_user_navbar'] = settings.get_user_navbar

# load jinja functions into scope
app.jinja_env.globals.update(poperr_get=bargate.core.poperr_get)

## Get the sections of the config file
app.load_share_config()
sharesList = app.sharesConfig.sections()

for section in sharesList:
	app.logger.debug("Creating share entry '" + str(section) + "'")
	app.add_url_rule(app.sharesConfig.get(section,'url'),endpoint=section,view_func=bargate.smb.share_handler,methods=['GET','POST'], defaults={'path': ''})
	app.add_url_rule(app.sharesConfig.get(section,'url') + '/<path:path>/',endpoint=section,view_func=bargate.smb.share_handler,methods=['GET','POST'])

app.sharesList = sharesList
