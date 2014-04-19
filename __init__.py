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
from logging.handlers import SMTPHandler
from logging.handlers import RotatingFileHandler
from logging import Formatter
from bargate.fapp import BargateFlask

################################################################################
#### Default config options

## Debug mode. This engages the web-based debug and disables logging.
DEBUG = False

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

## Kerberos configuration
KRB5_SERVICE = 'krbtgt/localdomain'
KRB5_DOMAIN  = 'localhost.localdomain'

## The 'workgroup' that SMBC should use for auth
SMB_WORKGROUP = 'MSHOME'

## Maximum file upload size
# 64MB by default
MAX_CONTENT_LENGTH = 64 * 1024 * 1024

## File 'types' we don't allow people to upload
BANNED_EXTENSIONS = set([
"ade", "adp", "bat", "chm", "cmd", "com", "cpl", "exe",
"hta", "ins", "isp", "jse", "lib", "mde", "msc", "msp",
"mst", "pif", "scr", "sct", "shb", "sys", "vb", "vbe",
"vbs", "vxd", "wsc", "wsf", "wsh"
])

## Logging and alerts
LOG_DIR='logs'
LOG_FILE='bargate.log'
EMAIL_ALERTS=False
ADMINS=['root']
SMTP_SERVER='localhost'
EMAIL_FROM='root'

## Redis
REDIS_ENABLED=True
REDIS_HOST='localhost'
REDIS_PORT=6379

## Disable the application or not
# Default to true if no config file to make sure a config file has been found.
DISABLE_APP=True

## Default bootstrap theme
THEME_DEFAULT='lumen'

################################################################################


# set up our application
app = BargateFlask(__name__)

# load default config
app.config.from_object(__name__)

# try to load config from various paths 
app.config.from_pyfile('/etc/bargate.conf', silent=True)
app.config.from_pyfile('/etc/bargate/bargate.conf', silent=True)
app.config.from_pyfile('/opt/bargate/bargate.conf', silent=True)
app.config.from_pyfile('/data/bargate/bargate.conf', silent=True)
app.config.from_pyfile('/data/fwa/bargate.conf', silent=True)

# set up e-mail alert logging
#if not app.debug:
if app.config['EMAIL_ALERTS'] == True:

	mail_handler = SMTPHandler(app.config['SMTP_SERVER'],
		app.config['EMAIL_FROM'],
		app.config['ADMINS'], 
		'Bargate Application Error')

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
	
## Set up file logging as well
file_handler = RotatingFileHandler(app.config['LOG_DIR'] + '/' + app.config['LOG_FILE'], 'a', 1 * 1024 * 1024, 10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.setLevel(logging.INFO)
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.info('bargate started up')


################################################################################

# load core functions
import bargate.core

# load anti csrf function reference into template engine
app.jinja_env.globals['csrf_token'] = core.generate_csrf_token 
app.jinja_env.globals['get_user_theme'] = core.get_user_theme

# import modules
import bargate.smb
import bargate.errors
import bargate.views
import bargate.smb_views
import bargate.mime

# load jinja functions into scope
app.jinja_env.globals.update(poperr_get=bargate.core.poperr_get)
