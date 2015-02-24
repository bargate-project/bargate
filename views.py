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
import bargate.core
from flask import Flask, request, session, redirect, url_for, flash, g, abort
import kerberos
import mimetypes
import os 
from random import randint
import time
import json
import re
import werkzeug

################################################################################
#### HOME PAGE / LOGIN PAGE

@app.route('/', methods=['GET', 'POST'])
@bargate.core.downtime_check
def login():
	if 'username' in session:
		return redirect(url_for(app.config['SHARES_DEFAULT']))
	else:
		if request.method == 'GET' or request.method == 'HEAD':
			next = request.args.get('next',default=None)
			bgnumber = randint(1,17)
			return bargate.core.render_page('login.html', next=next,bgnumber=bgnumber)

		elif request.method == 'POST':

			try:
				## Check password with kerberos
				kerberos.checkPassword(request.form['username'], request.form['password'], app.config['KRB5_SERVICE'], app.config['KRB5_DOMAIN'])
			except kerberos.BasicAuthError as e:
				flash('Incorrect username and/or password','alert-danger')
				return redirect(url_for('login'))
			except kerberos.KrbError as e:
				flash('Unexpected Kerberos Error: ' + e.__str__(),'alert-danger')
				return redirect(url_for('login'))
			except kerberos.GSSError as e:
				flash('Unexpected GSS Error: ' + e.__str__(),'alert-danger')
				return redirect(url_for('login'))

			## Set logged in (if we got this far)
			session['logged_in'] = True
			session['username']  = request.form['username']
			
			## Lower case all usernames so that keys in redis always match no matter what case-value the user enters
			session['username'] = session['username'].lower()

			## Check if the user selected "Log me out when I close the browser"
			permanent = request.form.get('sec',default="")

			## Set session as permanent or not
			if permanent == 'sec':
				session.permanent = True
			else:
				session.permanent = False

			## Encrypt the password and store in the session!
			session['id'] = bargate.core.aes_encrypt(request.form['password'],app.config['ENCRYPT_KEY'])

			## Log a successful login
			app.logger.info('User "' + session['username'] + '" logged in from "' + request.remote_addr + '" using ' + request.user_agent.string)

			## IF LDAP is enabled attempt to log the LDAP home
			if app.config['LDAP_HOMEDIR']:

				homedir = bargate.core.ldap_get_homedir(session['username'])
			
				## Try to get the home directory path for this user
				if homedir == None:
					app.logger.error('ldap_get_homedir returned None for user ' + session['username'])
					flash("Internal Error: I could not find your home directory!","alert-danger")
					return redirect(url_for('login'))
				else:
					session['ldap_homedir'] = homedir
					app.logger.info('User "' + session['username'] + '" LDAP home attribute ' + session['ldap_homedir'])

					if app.config['LDAP_HOMEDIR_IS_UNC']:
						if session['ldap_homedir'].startswith('\\\\'):
							session['ldap_homedir'] = session['ldap_homedir'].replace('\\\\','smb://',1)
						session['ldap_homedir'] = session['ldap_homedir'].replace('\\','/')
					## Overkill but log it again anyway just to make sure we really have the value we think we should
					app.logger.info('User "' + session['username'] + '" home SMB path ' + session['ldap_homedir'])
				
			## determine if "next" variable is set (the URL to be sent to)
			next = request.form.get('next',default=None)
			
			## Record the last login time
			bargate.settings.set_user_data('login',str(time.time()))

			if next == None:
				return redirect(url_for(app.config['SHARES_DEFAULT']))
			else:
				return redirect(next)

################################################################################
#### LOGOUT

@app.route('/logout')
@bargate.core.login_required
def logout():
	## Record the logout
	bargate.settings.set_user_data('logout',str(time.time()))
	
	## Log out of the session
	bargate.core.session_logout()
	
	## Tell the user
	flash('You were logged out successfully','alert-success')
	
	## redirect the user to the logon page
	return redirect(url_for('login'))

################################################################################
#### HELP PAGES

@app.route('/about')
def about():
	return bargate.core.render_page('about.html', active='help')

@app.route('/about/changelog')
def changelog():
	return bargate.core.render_page('changelog.html', active='help')

@app.route('/nojs')
def nojs():
	return bargate.core.render_page('nojs.html')
	
@app.route('/test')
def test():
	return bargate.core.render_page('test.html')

################################################################################
#### MIME MAP (DEVELOPER FUNCTION)

@app.route('/mime')
@bargate.core.downtime_check
@bargate.core.login_required
def mime():
	mimetypes.init()
	return bargate.core.render_page("mime.html",types=mimetypes.types_map,active="help")

################################################################################
#### BOOKMARKS

@app.route('/bookmarks', methods=['GET','POST'])
@bargate.core.login_required
@bargate.core.downtime_check
def bookmarks():
	bmKey = 'user:' + session['username'] + ':bookmarks'
	bmPrefix = 'user:' + session['username'] + ':bookmark:'

	if request.method == 'GET':
		bookmarks = bargate.settings.get_user_bookmarks()
		return bargate.core.render_page('bookmarks.html', active='user',pwd='',bookmarks = bookmarks)
		
	elif request.method == 'POST':
		action = request.form['action']
		
		if action == 'add':
		
			try:
				bookmark_name     = request.form['bookmark_name']
				bookmark_function = bargate.smb.check_name(request.form['bookmark_function'])
				bookmark_path     = bargate.smb.check_path(request.form['bookmark_path'])
				
			except KeyError as e:
				bargate.errors.fatal('Invalid Bookmark','You missed something on the previous page!')
			except ValueError as e:
				bargate.errors.fatal('Invalid Bookmark','Invalid bookmark name or bookmark value: ' + str(e))
				
			try:
				test_name = url_for(str(bookmark_function),path=bookmark_path)
			except werkzeug.routing.BuildError as ex:
				bargate.errors.fatal('Invalid Bookmark','Invalid function and/or path: ' + str(ex))

			g.redis.hset(bmPrefix + bookmark_name,'function',bookmark_function)
			g.redis.hset(bmPrefix + bookmark_name,'path',bookmark_path)
			g.redis.sadd(bmKey,bookmark_name)
		
			flash('Bookmark added successfully','alert-success')
			## return the user to the folder they were in
			return redirect(url_for(bookmark_function,path=bookmark_path))
			
		elif action == 'delete':
			bookmark_name     = request.form['bookmark_name']
			
			if g.redis.exists(bmKey):
				if g.redis.sismember(bmKey,bookmark_name):
				
					## Delete from the bookmarks key
					g.redis.srem(bmKey,bookmark_name)
					
					## Delete the bookmark hash
					g.redis.delete(bmPrefix + bookmark_name)
					
					## Let the user know and redirect
					flash('Bookmark deleted successfully','alert-success')
					return redirect(url_for('bookmarks'))

			flash('Bookmark not found!','alert-danger')
			return redirect(url_for('bookmarks'))					
