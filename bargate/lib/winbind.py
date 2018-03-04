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

import subprocess

from flask import current_app as app


def sid_to_name(sid):
	process = subprocess.Popen([app.config['WBINFO_BINARY'], '--sid-to-name', sid],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE)
	code = process.wait()
	sout, serr = process.communicate()

	if code == 0:
		sout = sout.rstrip()

		if sout.endswith(' 1') or sout.endswith(' 2'):
			return sout[:-2]
		else:
			return sout
	else:
		app.logger.warn("wbinfo returned an error: " + str(sout) + " " + str(serr))
		return "Unknown"
