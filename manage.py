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

from __future__ import print_function

import subprocess
import argparse
import os
import sys

from distutils.spawn import find_executable

JS_TEMPLATES_DIR = 'bargate/jstemplates'
JS_TEMPLATE_FILE = 'bargate/static/templates.js'
JAVASCRIPT_DIR   = 'bargate/static/js'
CSS_DIR          = 'bargate/static/css'
JSHINT_FILES     = ['bargate/static/js/bargate.js', 'bargate/static/js/login.js']


class Manager():
	def __init__(self):
		self.parser = argparse.ArgumentParser(prog='manage.py',
			description='manage.py',
			formatter_class=argparse.RawDescriptionHelpFormatter)
		self.parser.add_argument('function', metavar='function', type=str, help='the function to perform')
		self.parser.add_argument('-d', '--debug', action='store_true', help='turn on debugging output', dest='debug')

		self.args = self.parser.parse_args()

		try:
			method = getattr(self, 'cmd_' + self.args.function)
		except AttributeError:
			self.fatal("No function named '" + self.args.function + "'")

		method()

	def sysexec(self, command, shell=False):
		if self.debug:
			if type(command) is list:
				self.debug("Executing command " + str(" ".join(command)))
			else:
				self.debug("Executing command " + str(command))

		try:
			proc = subprocess.Popen(command,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				shell=shell,
				close_fds=True)
			(stdoutdata, stderrdata) = proc.communicate()
			if stdoutdata is None:
				stdoutdata = ""

			if self.args.debug:
				self.debug("command return code: " + str(proc.returncode))

			return (proc.returncode, str(stdoutdata))
		except Exception as ex:
			return (1, type(ex).__name__ + ": " + str(ex))

	def info(self, msg):
		print("INFO:  " + msg)

	def header(self, msg):
		print('\033[1mINFO:  ' + msg + '\033[0m')

	def debug(self, msg):
		if self.args.debug:
			print("DEBUG: " + msg)

	def error(self, msg):
		print("ERROR: " + msg)

	def fatal(self, msg=None):
		if msg:
			print("FATAL: " + msg)
		exit(1)

	def cmd_run(self):
		# I'd rather do bargate import app, app.run
		# but reloading is rather broken, as documented in the Flask docs.
		# so we'll use the 'flask' command.
		# from bargate import app
		# app.run()

		script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
		self.debug("Detected script directory as: " + script_dir)
		os.environ['PYTHON_PATH'] = script_dir
		os.environ['FLASK_APP'] = 'bargate'

		flask = find_executable("flask2")
		if not flask:
			flask = find_executable("flask")
			if not flask:
				self.fatal("Could not find the flask command. Please install it with: \nsudo pip install flask")

		self.debug('found flask at path: ' + flask)

		proc = subprocess.Popen([flask, 'run'], env=os.environ, close_fds=True)
		proc.communicate()

		if proc.returncode != 0:
			self.fatal("flask run returned an error")

	def cmd_dev(self):
		self.cmd_lint()
		self.cmd_build()
		self.cmd_run()

	def cmd_flake8(self):
		flake8 = find_executable("flake8-python2")
		if not flake8:
			flake8 = find_executable("flake8")
			if not flake8:
				self.fatal("Could not find the flake8 command. Please install it with: \nsudo pip install flake8")

		self.debug('found flake8 at path: ' + flake8)

		(result, output) = self.sysexec([flake8, '--ignore=E126,E128,E221,W191', '--max-line-length=120', '.'])

		if result == 0:
			self.info("flake8: PASS")
		else:
			print(output)
			self.fatal("flake8 returned errors")

	def cmd_jshint(self):
		jshint = find_executable("jshint")
		if not jshint:
			self.fatal("Could not find the jshint command. Please install it with: \nsudo npm install jshint -g")

		self.debug('found jshint at path: ' + jshint)

		for filename in JSHINT_FILES:
			self.debug("running jshint on " + filename)
			(result, output) = self.sysexec([jshint, filename])

			if result != 0:
				print(output)
				self.fatal("jshint returned errors")

		self.info("jshint: PASS")

	def cmd_csslint(self):
		csslint = find_executable("csslint")
		if not csslint:
			self.fatal("Could not find the csslint command. Please install it with: \nsudo npm install csslint -g")
		else:
			self.debug('found csslint at path: ' + csslint)

		files = os.listdir(CSS_DIR)
		if len(files) == 0:
			self.fatal("Did not find any files in " + CSS_DIR)

		for name in files:
			if name.endswith('.css'):
				if not name.endswith(".min.css"):
					self.debug("running csslint on " + CSS_DIR + "/" + name)

					(result, output) = self.sysexec([csslint, CSS_DIR + "/" + name, '--quiet',
						'--ignore=ids,order-alphabetical,unqualified-attributes'])

					if len(output) > 0:
						self.error(output)
						self.fatal("csslint returned errors")

		self.info("csslint: PASS")

	def cmd_nunjucks_precompile(self):
		nunjucks_precompile = find_executable("nunjucks-precompile")
		if not nunjucks_precompile:
			self.fatal("Could not find the nunjuncks-precompile command. Please install it with: \nsudo npm install nunjucks -g") # noqa
		else:
			self.debug('found nunjucks-precompile at path: ' + nunjucks_precompile)

		(result, output) = self.sysexec([nunjucks_precompile, JS_TEMPLATES_DIR])

		if result != 0:
			self.error(output)
			self.fatal("non-zero exit code from nunjucks")

		self.debug("writing out precompiled templates to " + JS_TEMPLATE_FILE)

		try:
			with open(JS_TEMPLATE_FILE, 'w') as f:
				f.write(output)
		except Exception as ex:
			self.fatal("Could not write to " + JS_TEMPLATE_FILE + ": " + str(ex))

		self.info("nunjucks templates precompiled")

	def cmd_uglifyjs(self):
		uglifyjs = find_executable("uglifyjs")
		if not uglifyjs:
			self.fatal("Could not find the uglifyfs command. Please install it with: \nsudo npm install uglify-js -g")
		else:
			self.debug('found uglifyjs at path: ' + uglifyjs)

		files = os.listdir(JAVASCRIPT_DIR)
		if len(files) == 0:
			self.fatal("Did not find any files in " + JAVASCRIPT_DIR)

		for name in files:
			if name.endswith('.js'):
				if not name.endswith(".min.js"):
					self.info("minifying " + JAVASCRIPT_DIR + "/" + name)
					new_name = name.replace(".js", ".min.js")

					(result, output) = self.sysexec([uglifyjs, '-c', '-m', '-o',
						JAVASCRIPT_DIR + "/" + new_name, '--', JAVASCRIPT_DIR + "/" + name])

					if result != 0:
						self.error(output)
						self.fatal("non-zero exit from uglifyjs")

	def cmd_crass(self):
		crass = find_executable("crass")
		if not crass:
			self.fatal("Could not find the crass command. Please install it with: \nsudo npm install crass -g")
		else:
			self.debug('found crass at path: ' + crass)

		files = os.listdir(CSS_DIR)
		if len(files) == 0:
			self.fatal("Did not find any files in " + CSS_DIR)

		for name in files:
			if name.endswith('.css'):
				if not name.endswith(".min.css"):
					self.info("minifying " + CSS_DIR + "/" + name)
					new_name = name.replace(".css", ".min.css")

					(result, output) = self.sysexec([crass, CSS_DIR + "/" + name, '--optimize'])

					if result != 0:
						self.error(output)
						self.fatal("non-zero exit from crass")

					self.debug("writing out minified CSS to " + CSS_DIR + "/" + new_name)
					try:
						with open(CSS_DIR + "/" + new_name, 'w') as f:
							f.write(output)
					except Exception as ex:
						self.fatal("Could not write to " + CSS_DIR + "/" + name + ": " + str(ex))

	def cmd_minify(self):
		self.cmd_uglifyjs()
		self.cmd_crass()

	def cmd_build(self):
		self.cmd_nunjucks_precompile()
		self.cmd_uglifyjs()
		self.cmd_crass()

	def cmd_lint(self):
		self.cmd_flake8()
		self.cmd_jshint()
		self.cmd_csslint()


if __name__ == '__main__':
	Manager()
