#!/usr/bin/python2
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

import os
from setuptools import find_packages, setup


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
	README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
	name='bargate',
	version='2.0.0',
	packages=find_packages(),
	include_package_data=True,
	license='GNU General Public License v3',
	description='Open source web interface to SMB file servers',
	long_description=README,
	url='https://bargate.io',
	author='David Bell',
	author_email='dave@evad.io',
	classifiers=[
		'Environment :: Web Environment',
		'Framework :: Flask',
		'Intended Audience :: Developers',
		'Intended Audience :: Education',
		'Intended Audience :: End Users/Desktop',
		'Intended Audience :: Information Technology',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Operating System :: POSIX :: Linux',
		'Programming Language :: Python',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
		'Topic :: Internet :: WWW/HTTP',
		'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
		'Topic :: Communications :: File Sharing',
		'Development Status :: 5 - Production/Stable',
		'Natural Language :: English',
	],
	project_urls={
		'Bug Tracker': 'https://github.com/divad/bargate/issues',
		'Documentation': 'https://bargate.io',
		'Source Code': 'https://github.com/divad/bargate',
	},
	install_requires=[
		'Flask>=0.12',
		'cryptography>=2.1.4',
		'pyyaml>=3.12',
	],
	extras_require={
		'previews': ["Pillow>=3.0"],
		'smbc': ["pysmbc>=1.0.15.5"],
		'pysmb': ["pysmb>=1.1.22"],
		'userdata': ["redis>=2.4"],
	}
)
