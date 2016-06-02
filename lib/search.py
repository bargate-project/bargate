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

from bargate import app
import bargate.lib.smb
import string, os, smbc, pprint, urllib, re, time
from flask import url_for

class RecursiveSearchEngine:

	def __init__(self,libsmbclient,func_name,path,path_as_str,srv_path_as_str,uri_as_str,query):
		self.libsmbclient    = libsmbclient
		self.func_name       = func_name
		self.path            = path
		self.path_as_str     = path_as_str
		self.srv_path_as_str = srv_path_as_str
		self.uri_as_str      = uri_as_str
		self.query           = query
		
		self.timeout_at      = int(time.time()) + app.config['SEARCH_TIMEOUT']
		self.timeout_reached = False
		self.results         = []

	def search(self):
		self._search(self.path,self.path_as_str,self.uri_as_str)
		return self.results, self.timeout_reached
		
	def _search(self,path, path_as_str, uri_as_str):

		## Try getting directory contents of where we are
		app.logger.debug("RecursiveSearchEngine: _search called to search: " + uri_as_str)
		try:
			directory_entries = self.libsmbclient.opendir(uri_as_str).getdents()
		except smbc.NotDirectoryError as ex:
			return

		except Exception as ex:
			app.logger.info("Search encountered an exception " + str(ex) + " " + str(type(ex)))
			return

		## now loop over each entry
		for dentry in directory_entries:

			## don't keep searching if we reach the timeout
			if self.timeout_reached:
				break;
			elif int(time.time()) >= self.timeout_at:
				self.timeout_reached = True
				break

			entry = bargate.lib.smb.loadDentry(dentry, self.srv_path_as_str, path, path_as_str)

			## Skip hidden files
			if entry['skip']:
				continue

			## Check if the filename matched
			if self.query.lower() in entry['name'].lower():
				app.logger.debug("RecursiveSearchEngine: Matched: " + entry['name'])
				entry = bargate.lib.smb.processDentry(entry, self.libsmbclient, self.func_name)
				entry['parent_path'] = path
				entry['parent_url']  = url_for(self.func_name,path=path)
				self.results.append(entry)

			## Search subdirectories if we found one
			if entry['type'] == 'dir':
				if len(path) > 0:
					new_path        = path + "/" + entry['name']
					new_path_as_str = path_as_str + "/" + entry['name_as_str']
				else:
					new_path        = entry['name']
					new_path_as_str = entry['name_as_str']					

				self._search(new_path, new_path_as_str, entry['uri_as_str'])
