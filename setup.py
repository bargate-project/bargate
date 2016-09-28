import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
	README = readme.read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
	name='bargate',
	version='1.5.3',
	packages=find_packages(),
	include_package_data=True,
	license='GNU General Public License v3',
	description='Open source modern web interface for SMB file servers',
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
	install_requires=[
		'Flask>=0.10',
		'pysmbc>=1.0.15.5',
		'pycrypto>=2.6.1',
		'Pillow>=3.0',
		'redis>=2.4',
	]
)
