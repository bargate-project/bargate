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

## returns true if this file type should be viewed in browser
def view_in_browser(mtype):
	"""Returns true if the file mime type passed to this function
	means that the file should be shown 'in browser'
	"""
	if mtype == 'application/pdf':
		## changed in oct 2013 becasue browsers like firefox dont have in-browser
		## pdf viewers and so the filename is barfed up - problem with flask's send_file
		return False
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

	## default type
	ficon = 'icon-file'

	if mtype.startswith('image'):
		ficon = 'icon-camera-retro'
	elif mtype.startswith('audio'):
		ficon = 'icon-music'
	elif mtype.startswith('video'):
		ficon = 'icon-film'
	elif mtype.startswith('message'):
		ficon = 'icon-envelope-alt'
	elif mtype.startswith('application'):
		ficon = 'icon-file-alt'

	return ficon

def mimetype_to_image(mtype):
	"""Converts a file mime type into an icon
	to be displayed next to the file name.
	"""

	## default type
	ficon = 'images/_blank.png'

	if mtype == 'image/bmp':
		ficon = 'images/bmp.png'
	if mtype == 'image/png':
		ficon = 'images/png.png'

	return ficon

def filename_to_mimetype(filename):
	"""Takes a filename and returns the mime type for the file based
	upon the file extension only.
	"""

	## guess a mimetype from python mimetypes
	(mtype,enc) = mimetypes.guess_type(filename)

	## If mimetypes module didn't detect anything
	if mtype == None:
		return ("Unknown file type","unknown")
	
	mimemap = {
		'application/msword' : 'Microsoft Word Document',
		'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : 'Microsoft Word Document XML',
		'application/vnd.openxmlformats-officedocument.presentationml.presentation' : 'Microsoft Powerpoint XML',
		'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'Microsoft Excel XML',
		'application/vnd.ms-powerpoint' : 'Microsoft Powerpoint',
		'application/octet-stream' : 'Binary file (executable or image)',
		'application/mathematica' : 'Mathematica File',
		'application/x-shockwave-flash' : 'Shockwave Flash',
		'application/vnd.visio' : 'Microsoft Visio',
		'application/vnd.ms-excel' : 'Microsoft Excel',
		
		'message/rfc822' : 'E-Mail Message',
		'text/calendar' : 'Calendar File',
		'application/x-java-archive' : 'Java Archive',
		'application/vnd.oasis.opendocument.presentation' : 'OpenDocument Presentation',
		'application/vnd.oasis.opendocument.spreadsheet' : 'OpenDocument Spreadsheet',

		'text/csv' : 'CSV - Comma Seperated Values',
		'text/css' : 'CSS - Cascading Style Sheet',
		'application/pdf' : 'PDF - Portable Document Format',
		'text/plain' : 'Plain text',
		'application/x-perl' : 'Perl File',
		'text/x-python' : 'Python File',
		'text/xml' : 'XML - eXtensible Markup Language',
		'application/xml' : 'XML - eXtensible Markup Language',
		'application/postscript' : 'Postscript',
		'text/html' : 'HTML - Hypertext Markup Language',
		'application/xhtml+xml' : 'XHTML - XML and HTML',

		'image/vnd.microsoft.icon' : 'Image - Microsoft Icon',
		'image/bmp' : 'Image - Microsoft Bitmap',
		'image/x-xpixmap' : 'Image - Pixmap',
		'image/png' : 'Image - PNG - Portable Network Graphics',
		'image/jpeg' : 'Image - JPEG',
		'image/gif' : 'Image - GIF',
		'image/tiff' : 'Image - TIFF',
		'image/svg' : 'Image - Scalable Vector Graphic (SVG)',

		'video/mp4' : 'Video - MPEG4',
		'video/mpeg' : 'Video - MPEG2',
		'video/ogg' : 'Video - OGG',
		'video/x-msvideo' : 'Video - AVI',
		'video/quicktime' : 'Video - Quicktime',

		'audio/x-wav' : 'Audio - WAV',
		'audio/x-ms-wma' : 'Audio - WMA - Windows Media Audio',
		'audio/mpeg' : 'Audio - MPEG',
		'audio/basic' : 'Audio - Basic',

		'application/x-gzip' : 'Compressed File - GZIP',
		'application/x-tar' : 'TAR Archive (TApe Archive)',
		'application/zip' : 'Compressed File - ZIP',
		'application/vnd.ms-cab-compressed' : 'Compressed File - Microsoft CABinet',
	}

	try:
		friendly = mimemap[mtype]
	except KeyError as e:
		friendly = mtype

	return (friendly,mtype)


