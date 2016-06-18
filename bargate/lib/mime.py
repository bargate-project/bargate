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
	'image/x-xpixmap', 'image/xpm'
]

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
	'application/vnd.oasis.opendocument.presentation' : 'Open Document Presentation',
	'application/vnd.oasis.opendocument.spreadsheet' : 'Open Document Spreadsheet',
	'application/vnd.oasis.opendocument.text' : 'Open Document Text',

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

	'image/vnd.microsoft.icon' : 'Microsoft Icon',
	'image/bmp' : 'Bitmap Image',
	'image/x-xpixmap' : 'Pixmap Image',
	'image/png' : 'PNG Image (Portable Network Graphics)',
	'image/jpeg' : 'JPEG Image',
	'image/gif' : 'GIF Image',
	'image/tiff' : 'TIFF Image',
	'image/svg' : 'SVG Image (Scalable Vector Graphic)',

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
	'application/x-tar' : 'File Archive - TAR',
	'application/zip' : 'Compressed File - ZIP',
	'application/vnd.ms-cab-compressed' : 'Compressed File - Microsoft CABinet',
}

## returns true if this file type should be viewed in browser
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

	## default type
	ficon = 'fa fa-fw fa-file-o'

	## IMAGES, AUDIO, VIDEO
	if mtype.startswith('image'):
		ficon = 'fa fa-fw fa-file-image-o'
		
	elif mtype.startswith('audio'):
		ficon = 'fa fa-fw fa-file-audio-o'
		
	elif mtype.startswith('video'):
		ficon = 'fa fa-fw fa-file-video-o'
		
	elif mtype.startswith('message'):
		ficon = 'fa fa-fw fa-envelope'
		
		
	## VISIO
	elif mtype.startswith('application/vnd.visio'):
		ficon = 'fa fa-fw fa-sitemap'		
		
	## EXECUTABLE FILES
	elif mtype.startswith('application/octet-stream'):
		ficon = 'fa fa-fw fa-cogs'
		
	## ARCHIVE FILES
	elif mtype.startswith('application/x-gzip'):
		ficon = 'fa fa-fw fa-file-archive-o'
	elif mtype.startswith('application/x-gtar'):
		ficon = 'fa fa-fw fa-file-archive-o'
	elif mtype.startswith('application/x-tar'):
		ficon = 'fa fa-fw fa-file-archive-o'
	elif mtype.startswith('application/zip'):
		ficon = 'fa fa-fw fa-file-archive-o'
	elif mtype.startswith('application/vnd.ms-cab-compressed'):
		ficon = 'fa fa-fw fa-file-archive-o'
	elif mtype.startswith('application/x-rpm'):
		ficon = 'fa fa-fw fa-file-archive-o'
		
	## SPREADSHEETS
	elif mtype.startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
		ficon = 'fa fa-fw fa-file-excel-o'
	elif mtype.startswith('application/vnd.ms-excel'):
		ficon = 'fa fa-fw fa-file-excel-o'
	elif mtype.startswith('application/vnd.oasis.opendocument.spreadsheet'):
		ficon = 'fa fa-fw fa-table'
				
	## WORD / WRITER
	elif mtype.startswith('application/msword'): 
		ficon = 'fa fa-fw fa-file-word-o'
	elif mtype.startswith('application/vnd.openxmlformats-officedocument.wordprocessingml.document'): 
		ficon = 'fa fa-fw fa-file-word-o'
	elif mtype.startswith('application/vnd.oasis.opendocument.text'): 
		ficon = 'fa fa-fw fa-file-text-o'		
			
	## PRESENTATIONS		
	elif mtype.startswith('application/vnd.ms-powerpoint'):
		ficon = 'fa fa-fw fa-file-powerpoint-o'
	elif mtype.startswith('application/vnd.openxmlformats-officedocument.presentationml.presentation'):
		ficon = 'fa fa-fw fa-file-powerpoint-o'
	elif mtype.startswith('application/vnd.oasis.opendocument.presentation'):
		ficon = 'fa fa-fw fa-slideshare'
		
	## PDF
	elif mtype.startswith('application/pdf'):
		ficon = 'fa fa-fw fa-file-pdf-o'	

	## Text/html
	elif mtype.startswith('text/html'):
		ficon = 'fa fa-fw fa-file-code-o'
	elif mtype.startswith('application/xhtml+xml'):
		ficon = 'fa fa-fw fa-file-code-o'
	elif mtype.startswith('text/css'):
		ficon = 'fa fa-fw fa-file-code-o'
		
	## XML
	elif mtype.startswith('text/xml') or mtype.startswith('application/xml'):
		ficon = 'fa fa-fw fa-code-o'
		
	## Code
	elif mtype.startswith('application/x-perl'):
		ficon = 'fa fa-fw fa-file-code-o'
	elif mtype.startswith('application/x-python'):
		ficon = 'fa fa-fw fa-file-code-o'
	elif mtype.startswith('text/x-python'):
		ficon = 'fa fa-fw fa-file-code-o'
	elif mtype.startswith('application/x-perl'):
		ficon = 'fa fa-fw fa-file-code-o'
	elif mtype.startswith('application/x-sh'):
		ficon = 'fa fa-fw fa-terminal'
		
	elif mtype.startswith('text/plain'):
		ficon = 'fa fa-fw fa-file-text-o'
		
	## generic application
	elif mtype.startswith('application'):
		ficon = 'fa fa-fw fa-cog'
		
	return ficon

def filename_to_mimetype(filename):
	"""Takes a filename and returns the mime type for the file based
	upon the file extension only.
	"""
	
	## guess a mimetype from python mime types
	(mtype,enc) = mimetypes.guess_type(filename,strict=False)

	## If mimetypes module didn't detect anything
	if mtype == None:
		return ("Unknown file type","unknown")
	
	try:
		friendly = mimemap[mtype]
	except KeyError as e:
		friendly = mtype

	return (friendly,mtype)


