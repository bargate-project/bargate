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

import mimetypes

pillow_supported = ['image/bmp', 'image/x-windows-bmp', 'application/postscript',
	'image/gif', 'image/jpeg', 'image/x-pcx', 'image/png', 'image/x-portable-pixmap',
	'image/tiff', 'image/x-tiff', 'image/x-xbitmap', 'image/x-xbm', 'image/xbm',
	'image/x-xpixmap', 'image/xpm']

mimemap = {
	'application/msword': 'Microsoft Word Document',
	'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Microsoft Word Document XML',
	'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'Microsoft Powerpoint XML',
	'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Microsoft Excel XML',
	'application/vnd.ms-powerpoint': 'Microsoft Powerpoint',
	'application/octet-stream': 'Binary file (executable or image)',
	'application/mathematica': 'Mathematica file',
	'application/x-shockwave-flash': 'Shockwave Flash',
	'application/vnd.visio': 'Microsoft Visio',
	'application/vnd.ms-excel': 'Microsoft Excel',
	'message/rfc822': 'E-Mail message',
	'text/calendar': 'Calendar file',
	'application/x-java-archive': 'Java archive',
	'application/vnd.oasis.opendocument.presentation': 'Open document presentation',
	'application/vnd.oasis.opendocument.spreadsheet': 'Open document spreadsheet',
	'application/vnd.oasis.opendocument.text': 'Open document text',
	'text/csv': 'Comma seperated values (CSV)',
	'text/css': 'Cascading style sheet (CSV)',
	'application/pdf': 'Portable document format (PDF)',
	'text/plain': 'Plain text',
	'application/x-perl': 'Perl file',
	'text/x-python': 'Python file',
	'text/xml': 'XML - eXtensible markup language',
	'application/xml': 'XML - eXtensible markup language',
	'application/postscript': 'Postscript',
	'text/html': 'HTML - Hypertext markup language',
	'application/xhtml+xml': 'XHTML',
	'image/vnd.microsoft.icon': 'Microsoft icon',
	'image/bmp': 'Bitmap image',
	'image/x-xpixmap': 'Pixmap image',
	'image/png': 'PNG image (Portable Network Graphics)',
	'image/jpeg': 'JPEG image',
	'image/gif': 'GIF image',
	'image/tiff': 'TIFF image',
	'image/svg': 'SVG image (Scalable Vector Graphic)',
	'video/mp4': 'MPEG4 video',
	'video/mpeg': 'MPEG2 video',
	'video/ogg': 'OGG video',
	'video/x-msvideo': 'AVI video',
	'video/quicktime': 'Quicktime video',
	'audio/x-wav': 'WAV audio',
	'audio/x-ms-wma': 'Windows media audio',
	'audio/mpeg': 'MPEG audio',
	'audio/basic': 'Basic audio',
	'application/x-gzip': 'GZIP compressed file',
	'application/x-tar': 'File (tape) archive',
	'application/zip': 'ZIP compressed file',
	'application/vnd.ms-cab-compressed': 'Microsoft cabinet archive',
	'application/x-iso9660-image': 'ISO disk image',
}


def view_in_browser(mtype):
	"""Returns true if the file mime type passed to this function
	means that the file should be shown 'in browser'
	"""

	if mtype == 'application/pdf':
		return True
	elif mtype == 'text/plain':
		return True
	elif mtype.startswith('image'):
		return True
	else:
		return False


def mimetype_to_icon(mtype):
	"""Converts a file mime type into an icon
	to be displayed next to the file name.
	"""

	ficon = 'far fa-file-alt'

	if mtype.startswith('image'):
		ficon = 'far fa-file-image'
	elif mtype.startswith('audio'):
		ficon = 'far fa-file-audio'
	elif mtype.startswith('video'):
		ficon = 'far fa-file-video'
	elif mtype.startswith('message'):
		ficon = 'far fa-envelope-open'
	elif mtype.startswith('application/vnd.visio'):
		ficon = 'fas fa-sitemap'
	elif mtype.startswith('application/octet-stream'):
		ficon = 'fas fa-cogs'
	elif mtype.startswith('application/x-gzip'):
		ficon = 'far fa-file-archive'
	elif mtype.startswith('application/x-gtar'):
		ficon = 'far fa-file-archive'
	elif mtype.startswith('application/x-tar'):
		ficon = 'far fa-file-archive'
	elif mtype.startswith('application/zip'):
		ficon = 'far fa-file-archive'
	elif mtype.startswith('application/vnd.ms-cab-compressed'):
		ficon = 'far fa-file-archive'
	elif mtype.startswith('application/x-rpm'):
		ficon = 'far fa-file-archive'
	elif mtype.startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
		ficon = 'far fa-file-excel'
	elif mtype.startswith('application/vnd.ms-excel'):
		ficon = 'far fa-file-excel'
	elif mtype.startswith('application/vnd.oasis.opendocument.spreadsheet'):
		ficon = 'far fa-file-excel'
	elif mtype.startswith('application/msword'):
		ficon = 'far fa-file-word'
	elif mtype.startswith('application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
		ficon = 'far fa-file-word'
	elif mtype.startswith('application/vnd.oasis.opendocument.text'):
		ficon = 'far fa-file-alt'
	elif mtype.startswith('application/vnd.ms-powerpoint'):
		ficon = 'far fa-file-powerpoint'
	elif mtype.startswith('application/vnd.openxmlformats-officedocument.presentationml.presentation'):
		ficon = 'far fa-file-powerpoint'
	elif mtype.startswith('application/vnd.oasis.opendocument.presentation'):
		ficon = 'far fa-file-powerpoint'
	elif mtype.startswith('application/pdf'):
		ficon = 'far fa-file-pdf'
	elif mtype.startswith('text/html'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('application/xhtml+xml'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('text/css'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('text/xml') or mtype.startswith('application/xml'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('application/x-perl'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('application/x-python'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('text/x-python'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('application/x-perl'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('application/x-sh'):
		ficon = 'far fa-file-code'
	elif mtype.startswith('text/plain'):
		ficon = 'far fa-file-alt'
	elif mtype.startswith('application/x-iso9660-image'):
		ficon = 'fas fa-file-archive'
	elif mtype.startswith('application'):
		ficon = 'fas fa-cog'
	return ficon


def filename_to_mimetype(filename):
	"""Takes a filename and returns the mime type for the file based
	upon the file extension only.
	"""

	# guess a mimetype from python mime types
	(mtype, enc) = mimetypes.guess_type(filename, strict=False)

	# If mimetypes module didn't detect anything
	if mtype is None:
		return ("Unknown", "unknown")

	try:
		friendly = mimemap[mtype]
	except KeyError:
		friendly = mtype

	return (friendly, mtype)
