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

from flask import current_app as app

from bargate.lib import fs, userdata, mime


class DirectoryEntry(object):
	def __init__(self, name):
		self.name = name

	@property
	def skip(self):
		if self.name == '.' or self.name == '..':
			return True

		if not userdata.get_show_hidden_files():
			if self.name.startswith('.'):
				return True
			if self.name.startswith('~$'):
				return True
			if self.name in ['desktop.ini', '$RECYCLE.BIN', 'RECYCLER', 'Thumbs.db']:
				return True

			if self.type == fs.TYPE_SHARE:
				if self.name.endswith == "$":
					return True

		if self.type not in [fs.TYPE_FILE, fs.TYPE_DIR, fs.TYPE_DIR]:
			return True

		return False

	def to_dict(self, path='', include_path=False):
		data = {'name': self.name, 'type': self.type, 'skip': False}

		if self.skip:
			data['skip'] = True
		else:
			data['skip'] = False

			if include_path:
				if not path:
					data['path'] = self.name
				else:
					data['path'] = path + '/' + self.name

			if self.type is fs.TYPE_FILE:
				(htype, mtype) = mime.filename_to_mimetype(self.name)
				data['icon'] = mime.mimetype_to_icon(mtype)

				data['mtype'] = htype
				data['atime'] = self.atime
				data['mtime'] = self.mtime
				data['size'] = self.size

				if app.config['IMAGE_PREVIEW'] and mtype in mime.pillow_supported:
					if self.size <= app.config['IMAGE_PREVIEW_MAX_SIZE']:
						data['img'] = True

				if mime.view_in_browser(mtype):
					data['view'] = True

		return data
