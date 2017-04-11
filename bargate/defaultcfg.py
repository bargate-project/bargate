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

from datetime import timedelta

## Bargate version number
VERSION='1.5.6'

## Debug mode. This engages the web-based debug mode
DEBUG = False

## Enable the debug toolbar. DO NOT DO THIS ON A PRODUCTION SYSTEM. EVER. It exposes SECRET_KEY and ENCRYPT_KEY.
DEBUG_TOOLBAR = False

## Many errors don't show a full stack trace as they show a redirected 'error popup'. Set this to True to disable that behaviour and show full errors.
DEBUG_FULL_ERRORS = False

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

## Default directory layout mode
## either 'grid' or 'list'
LAYOUT_DEFAULT='grid'

## Flask defaults (changed to what we prefer)
SESSION_COOKIE_SECURE      = True
SESSION_COOKIE_HTTPONLY    = True
PREFERRED_URL_SCHEME       = 'https'
USE_X_SENDFILE             = False
PERMANENT_SESSION_LIFETIME = timedelta(days=7)
SEND_FILE_MAX_AGE_DEFAULT  = 0

## Shares config file
SHARES_CONFIG='/etc/bargate/shares.conf'
SHARES_DEFAULT='custom'

## Local templates to override built in ones
LOCAL_TEMPLATE_DIR=False

## Local static files directory
LOCAL_STATIC_DIR=False

## Use a local favicon (you don't need to set this, it is determined automatically)
LOCAL_FAVICON=False

# Name of the app to display everywhere
APP_DISPLAY_NAME='Bargate'
APP_DISPLAY_NAME_SHORT='Bargate'

## What auth method. "ldap", "kerberos", 'krb5' (alias) or 'smb'
AUTH_TYPE='ldap'

## LDAP AUTH
LDAP_URI            = 'ldaps://localhost.localdomain'
LDAP_SEARCH_BASE    = ''
LDAP_USER_ATTRIBUTE = 'sAMAccountName' ## default to AD style as lets face it, sadly, most people use it :'(
LDAP_ANON_BIND      = True
LDAP_BIND_USER      = ''
LDAP_BIND_PW        = ''

## LDAP homedir attribute support
# You MUST use AUTH_TYPE 'ldap' or this setting will be ignored
LDAP_HOMEDIR        = False
LDAP_HOME_ATTRIBUTE = 'homeDirectory' ## default to AD style as lets face it, sadly, most people use it :'(
LDAP_HOMEDIR_IS_UNC = True

## KERBEROS AUTH
# you should probably use LDAP auth...
KRB5_SERVICE = 'krbtgt/localdomain'
KRB5_DOMAIN  = 'localhost.localdomain'

## SMB AUTH
# only use this if you don't have LDAP or kerberos
SMB_AUTH_URI = "smb://yourdomain.tld/NETLOGON/"

## TOTP 2-factor auth
TOTP_ENABLED = False
TOTP_IDENT   = 'bargate'

## REMEMBER_ME_ENABLED - "Remember me on this computer" enabled or not.
REMEMBER_ME_ENABLED = True

## Image previews
IMAGE_PREVIEW=True

## Max image preview size in bytes
IMAGE_PREVIEW_MAX_SIZE=30*1024*1024

## Should bargate attempt to use winbind to resolve a SID to a name?
WBINFO_LOOKUP=False
WBINFO_BINARY='/usr/bin/wbinfo'

## Allow searches?
SEARCH_ENABLED=False

## Maximum time to search for before giving up and returning results
SEARCH_TIMEOUT=50
