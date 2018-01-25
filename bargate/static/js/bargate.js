var $user = {hidden: false, overwrite: false, twostep: false};
var $config = {};
var dragCounter = 0;

function set_body_padding() {
	$('body').css('padding-top', $('#nav').outerHeight(true));
}

var $err = {
	show: function(title, desc) {
		$mdl.draw('error', {title: title, desc: desc}).show();
	},
	fail: function(title, message, jqXHR, textStatus, errorThrown) {
		if (jqXHR.status === 0) {
			reason = "a network error occured.";
		} else if (jqXHR.status === 400) {
			reason = "the server said 'Bad Request'";
		} else {
			reason = textStatus;
		}

		this.show(title, message + ": " + reason);
	},
	nonzero: function(title, message, code) {

		if (code == 401) {
			location.reload(true); // redirect to login
		} else {
			this.show(title, message);
		}
	},
};

var $mdl = {
	draw: function (name, data) {
		$('#mdl-d').removeClass('modal-lg');

		if (!data) { data = {}; }
		data.config = $config;
		data.user = $user;

		$('#mdl-c').html(nunjucks.render("modals/" + name + '.html', data));

		$click.bind('#mdl-c');
		$fsub.bind('#mdl-c');
		$entry.bind('#mdl-c');

		return this;
	},
	show: function () {
		$('#mdl').modal('show');
		contents = $('#mdl .mfocus').val();
		$('#mdl .mfocus').focus().val("").val(contents);
		return this;
	},
	hide: function () {
		$('#mdl').modal('hide');
	},
	lg: function () {
		$('#mdl-d').addClass('modal-lg');
	}
};

function ts2str(timestamp) {
	d = new Date(timestamp * 1000);
	yr = d.getFullYear();
	mo = ('0' + (d.getMonth() + 1)).slice(-2);
	da = ('0' + d.getDate()).slice(-2);
	hs = ('0' + d.getHours()).slice(-2);
	ms = ('0' + d.getMinutes()).slice(-2);
	return yr + '-' + mo + '-' + da + ', ' + hs + ':' + ms;
}

function filesizeformat(bytes) {
	bytes = parseFloat(bytes);
	units = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

	if (bytes === 1) {
		return '1 Byte';
	} else if (bytes < 1024) {
		return bytes + ' Bytes';
	} else {
		return units.reduce(function (match, unit, index) {
			var size = Math.pow(1024, index);
			if (bytes >= size) {
				return (bytes/size).toFixed(1) + ' ' + unit;
			}
			return match.replace(".0 "," ");
		});
	}
}

var $dir = {
	sortBy: 'name',

	draw: function() {
		try {
			window.stop();
		} catch (exception) {
			document.execCommand('Stop');
		}
		
		$('#crumbs').html(nunjucks.render('breadcrumbs.html', { crumbs: this.data.crumbs, root_name: this.data.root_name }));

		if (this.data.no_items) {
			$('#main').html(nunjucks.render('empty.html'));
		} else {
			$('#main').html(nunjucks.render('directory-' + $user.layout + '.html', {dirs: this.data.dirs, files: this.data.files, shares: this.data.shares, buildurl: buildurl}));
		}

		if ($user.layout == "list") {
			this.draw_list();
		}
		else {
			this.draw_grid();
		}

		this.bind();
		set_body_padding();
	},

	draw_list: function() {
		var self = this;
		function nameToNum (by) {
			if (by == 'name') { return [4, "asc"]; }
			else if (by == 'mtime') { return [5, "asc"]; }
			else if (by == 'type') { return [6, "asc"]; }
			else if (by == 'size') { return [7, "asc"]; }
		}

		$("[data-sort]").on('click', function(e) {
			e.preventDefault();
			sortby = $(this).data('sort');
			self.sortBy = sortby;
			$('#dir').DataTable().order(nameToNum(sortby)).draw();
			$('[data-sort] > span').addClass('d-none');
			$('[data-sort="' + sortby + '"] > span').removeClass('d-none');
		});

		$('#dir').DataTable( {
			"paging": false,
			"searching": false,
			"info": false,
			"columns": [
				{ "orderable": false },
				{ "orderable": false },
				{ "orderable": false },
				{ "orderable": false },
				{ "visible": false},
				{ "visible": false},
				{ "visible": false},
				{ "visible": false},
			],
			"order": [nameToNum(this.sortBy)],
			"dom": 'lrtip'
		});
	},

	draw_grid: function() {
		var self = this;
		var $container = $('#files').isotope({
			getSortData: {
				name: '[data-sortname]',
				type: '[data-mtyper]',
				mtime: '[data-mtime] parseInt',
				size: '[data-sizer] parseInt',
			},
			transitionDuration: '0.2s',
			percentPosition: true,
			sortAscending: {
				name: true,
				type: true,
				mtime: false,
				size: false
			},
			sortBy: this.sortBy,
		});

		$("[data-sort]").on('click', function(e) {
			e.preventDefault();
			sortby = $(this).data('sort');
			self.sortBy = sortby;
			$container.isotope({ sortBy: sortby });
			$('[data-sort] > span').addClass('d-none');
			$('[data-sort="' + sortby + '"] > span').removeClass('d-none');
		});

		var $dirs = $('#dirs').isotope( {
			getSortData: { name: '[data-sortname]',},
			sortBy: 'name',
		});
	},

	bind: function() {
		$click.bind('#main');
		$click.bind('#crumbs');

		/* right click menu for files */
		$('[data-ctx="file"]').contextMenu({
			menu: "#ctx-menu-file",
			hide: "#ctx-menu-dir",
			func: function (item, selectedMenu) {
				file = item.closest('[data-ctx="file"]');
				action = selectedMenu.closest("a").data('action');

				if (action == 'view' ) {
					window.open(get_url(file, 'view'),'_blank');
				} else if ( action == 'download') {
					window.location.href = get_url(file, 'download');
				} else {
					$entry.action(action, file, 'file');
				}
			}
		});

		/* context menu for directories */
		$('[data-ctx="dir"]').contextMenu({
			menu: "#ctx-menu-dir",
			hide: "#ctx-menu-file",
			func: function (invokedOn, selectedMenu) {
				sdir = invokedOn.closest('[data-ctx="dir"]');
				action = selectedMenu.closest("a").data('action');

				if (action == 'open') {
					$dir.load($dir.epname, get_path(sdir));
				} else {
					$entry.action(action, sdir, 'dir');
				}
			}
		});
	},

	load: function(epname, path, alterHist) {
		var self = this;
		if (alterHist === undefined) { alterHist = true; }

		$.getJSON('/xhr/ls/' + epname + '/' + path)
		.done(function(data) {
			if (data.code > 0) {
				$err.nonzero("Unable to open directory", data.msg, data.code);
			} else {
				if (data.bmark) {
					$('[data-click="bmark"]').removeClass('disabled');
				} else {
					$('[data-click="bmark"]').addClass('disabled');
				}

				// make sure the switch layout button is enabled
				$('.b-layout').attr("disabled", false).removeClass("disabled");

				if (data.shares) {
					self.mode = 'shares';
					$('.b-dir').attr("disabled", true).addClass("disabled");
					$('.b-search').attr("disabled", true).addClass("disabled");
				} else {
					self.mode = 'dir';
					$('.b-dir').attr("disabled", false).removeClass("disabled");
					$('.b-search').attr("disabled", false).removeClass("disabled");
				}

				self.data = data;
				self.epurl = data.epurl;
				self.epname = epname;
				self.path  = path;

				self.draw();
				bind_upload_trigger();

				if (alterHist) {
					new_url = data.epurl + '/browse/' + path;
					history.pushState({epname: epname, epurl: data.epurl, path: path}, '', new_url);
				}
			}
		})
		.fail(function(jqXHR, textStatus, errorThrown) {
			$err.fail("Unable to open folder", "Could not load folder contents", jqXHR, textStatus, errorThrown);
		});
	},

	reload: function() {
		if (this.mode == 'dir') {
			this.load(this.epname, this.path, false);
		}
	},

	onchange: function() {
		if (this.mode == 'dir') {
			this.reload();
		} else if (this.mode == 'search') {
			// when in search mode: go to the dir (might be the same dir) where the item was selected
			$dir.load($dir.epname, $entry.path);
		}
	},

	post: function(params, desc, callback) {
		params.epname = this.epname;
		params._csrfp_token = $user.token;

		$.post( '/xhr', params)
			.fail(function(jqXHR, textStatus, errorThrown) {
				$err.fail("Error", "Unable to " + desc, jqXHR, textStatus, errorThrown);
			})
			.done(function(data, textStatus, jqXHR) {
				if (data.code !== 0) {
					$err.nonzero("Unable to " + desc, data.msg, data.code);
				} else {
					$mdl.hide();
					if (data.msg) {
						notifyOK(data.msg);
					}
					callback(data);
				}
			});
	},
};

function bind_upload_trigger() {
	$('#upload-i').fileupload({
		url: '/xhr',
		dataType: 'json',
		maxChunkSize: 10485760, // 10MB
		formData: [{name: '_csrfp_token', value: $user.token}, {name: 'action', value: 'upload'}, {name: 'epname', value: $dir.epname}, {name: 'path', value: $dir.path}],
		stop: function (e, data) {
			window.uploadNotify.close();
			delete window.uploadNotify;
			if (window.numUploadsDone > 1) {
				notifyOK(window.numUploadsDone + " files uploaded");
			}
		},
		done: function (e, data) {
			$.each(data.result.files, function (index, file) {
				if (file.error) {
					notifyErr("Upload of '" + file.name + "' failed: " + file.error);
				}
				else {
					window.numUploadsDone = window.numUploadsDone + 1;
					if (window.numUploads == 1) {
						notifyOK("Uploaded " + file.name);
					}

					$dir.reload();
				}
			});
		},
		fail: function (e, data) {
			if (data.errorThrown != 'abort') {
				notifyErr("Upload failed: " + data.errorThrown);
			}
		},
		progressall: function (e, data) {
			progress = parseInt(data.loaded / data.total * 100, 10);
			window.uploadNotify.update('progress', progress);
			window.uploadNotify.update('message', progress + "% " + filesizeformat(data.loaded) + ' out of ' + filesizeformat(data.total));
		},
		add: function (e, data) {
			if ($dir.mode != 'dir') {
				$err.show("Cannot upload", "You must navigate to a directory to upload files");
			}
			dragCounter = 0;
			$mdl.hide();

			if (window.uploadNotify === undefined) {
				window.uploadNotify = $.notify({ icon: 'fas fa-fw fa-cloud-upload-alt', message: '', title: 'Uploading one file <button class="pull-right btn btn-xs btn-warning upload-cancel-b">Cancel</button><br>' },
					{ allow_dismiss: false, showProgressbar: true, delay: 0, type: 'info', placement: {align: 'center', from: 'bottom'},
					template: nunjucks.render('notify.html') });
				window.numUploads = 1;
				window.numUploadsDone = 0;
				window.uploads = [];
			} else {
				if (window.numUploads === 0) {
					window.numUploads = 1;
					window.uploadNotify.update('title','Uploading one file <button class="pull-right btn btn-xs btn-warning upload-cancel-b">Cancel</button><br>');
				} else {
					window.numUploads = window.numUploads + 1;
					window.uploadNotify.update('title','Uploading ' + window.numUploads + ' files <button class="pull-right btn btn-xs btn-warning upload-cancel-b">Cancel</button><br>');
				}
			}

			if (window.uploads === undefined) {
				window.uploads = [];
			}

			promise = data.submit();
			window.uploads.push(promise);

			$('.upload-cancel-b').click(function (e) {
				for (i=0; i < window.uploads.length; i++)
				{
					window.uploads[i].abort();
				}
				if (window.numUploads == 1) {
					notifyErr("Upload cancelled");
				} else {
					notifyErr("Uploads cancelled");
				}
			});
		},
	}).prop('disabled', !$.support.fileInput).parent().addClass($.support.fileInput ? undefined : 'disabled');
}

function get_path(entry) {
	if (entry.data('path')) {
		return entry.data('path');
	} else {
		if ($dir.path) { 
			return $dir.path + "/" + entry.data('name');
		} else {
			return entry.data('name');
		}
	}
}

function get_url(entry, action) {
	return $dir.epurl + "/" + action + "/" + get_path(entry);
}

function buildurl(name, action) {
	return $dir.epurl + "/" + action + "/" + $dir.path + "/" + name;
}

function notifyOK(msg) {
	$.notify({ icon: 'fas fa-fw fa-check', message: msg },{ type: 'success', template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

function notifyErr(msg) {
	$.notify({ icon: 'fas fa-fw fa-exclamation-triangle', message: msg },{ type: 'danger', delay: 10000, template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

var $fsub = {
	bind: function(selector) {
		var self = this;
		if (selector) { selector = selector + ' '; } else { selector = ''; }

		$(selector + "[data-fsub]").submit(function (e) {
			e.preventDefault();
			self[$(this).data('fsub')](e);
		});
	},

	rename: function() {
		$dir.post({action: 'rename', path: $entry.path, old_name: $entry.name, new_name: $('#e-rename-i').val()}, 'rename', function () { $dir.onchange(); });
	},

	copy: function() {
		$dir.post({action: 'copy', path: $entry.path, src: $entry.name, dest: $('#e-copy-i').val()}, 'copy file', function () { $dir.onchange(); });
	},

	delete: function() {
		$dir.post({action: 'delete', path: $entry.path, name: $entry.name}, 'delete', function () { $dir.onchange(); });
	},

	mkdir: function() {
		$dir.post({action: 'mkdir', path: $dir.path, name: $('#mkdir-i').val()}, 'create directory', function () { $dir.onchange(); });
	},

	bmark: function() {
		$dir.post({action: 'bookmark', path: $dir.path, name: $('#bmark-i').val()}, 'create bookmark', function (data) { 
			$('.bmarks').append('<li><a href="' + data.url + '"><i class="fas fa-arrow-right fa-fw"></i>' + $('#bmark-i').val() + '</a></li>');
		});
	},

	connect: function() {
		$dir.post({action: 'connect', path: $('#connect-i').val()}, 'connect to server', function () { $dir.load('custom', ''); });
	},

	search: function() {
		$.getJSON('/xhr/search/' + $dir.epname + '/' + $dir.path, {q: $('#search-i').val()})
		.done(function(data) {
			if (data.code > 0) {
				$err.nonzero("Search failed", data.msg, data.code);
			} else {
				$mdl.hide();
				$dir.data = data;

				$dir.mode = "search";
				$('.b-dir').attr("disabled", true).addClass("disabled");
				$('.b-layout').attr("disabled", true).addClass("disabled");
				$('[data-click="bmark"]').addClass('disabled');

				$('#main').html(nunjucks.render('search.html', data));

				$('#results').DataTable({
					"paging": false,
					"searching": false,
					"info": false,
					"ordering": false,
					"dom": 'lrtip'
				});

				$dir.bind();
			}
		})
		.fail(function(jqXHR, textStatus, errorThrown) {
			$err.fail("Unable to search", "Could not obtain search results", jqXHR, textStatus, errorThrown);
		});
	},

	totp_enable: function() {
		$.post( '/totp/enable', { _csrfp_token: $user.token, token: $('#twostep-enable-i').val()})
			.fail(function(jqXHR, textStatus, errorThrown) {
				$err.fail("Network error", "Could not enable two-step verification", jqXHR, textStatus, errorThrown);
			})
			.done(function(data, textStatus, jqXHR) {
				if (data.code !== 0) {
					$err.nonzero("Unable to enable two-step verification", data.msg, data.code);
				} else {
					$settings.modal();
				}
		});
	},

	totp_disable: function() {
		$.post( '/totp/disable', { _csrfp_token: $user.token, token: $('#twostep-disable-i').val()})
			.fail(function(jqXHR, textStatus, errorThrown) {
				$err.fail("Network error", "Could not disable two-step verification", jqXHR, textStatus, errorThrown);
			})
			.done(function(data, textStatus, jqXHR) {
				if (data.code !== 0) {
					$err.nonzero("Unable to disable two-step verification", data.msg, data.code);
				} else {
					$settings.modal();
				}
		});
	},

};

var $settings = {
	modal: function() {
		var self = this;
		$mdl.draw('settings');

		$('input[name=layout-r]').change(function() {
			self.layout(this.value);
		});

		$('#hidden-c').change(function() {
			self.save('hidden', this.checked, function (data) { 
				$dir.reload();
			});
		});

		$('input[name=click-r]').change(function() {
			self.save('click', this.value, function (data) { 
				$dir.reload();
			});
		});

		$('#overwrite-c').change(function() {
			self.save('overwrite', this.checked);
		});

		$('input[name=theme-r]').change(function() {
			self.theme(this.value);
		});

		$mdl.show().lg();
	},
	save: function(key, value, callback) {
		$.post( "/xhr/data", { key: key, value: value, _csrfp_token: $user.token })
			.fail(function(jqXHR, textStatus, errorThrown) {
				$err.fail("Settings error", "Unable to save settings", jqXHR, textStatus, errorThrown);
			})
			.done(function(data, textStatus, jqXHR) {
				if (data.code !== 0) {
					$err.nonzero("Settings error", data.msg, data.code);
				} else {
					$user[key] = value;
					callback(data);
				}
			});
	},
	layout: function(name) {
		var self = this;
		this.save('layout', name, function (data) { 
			$user.layout = newLayout;
			self.set_layout_cls();
			$dir.draw();
		});
	},
	set_layout_cls: function() {
		if ($user.layout == "grid") {
			$(".layout-ico").removeClass("fa-th-large").addClass("fa-list");
		} else {
			$(".layout-ico").removeClass("fa-list").addClass("fa-th-large");
		}
	},
	theme: function(name) {
		if (name == $user.theme) { return; }

		this.save('theme', name, function (data) { 
			$("body").fadeOut(100, function() {
				$("body").css('display', 'none');
				$("#theme-l").attr("href", "/static/themes/" + name + "/bootstrap.min.css");
				$("#theme-o-l").attr("href", "/static/themes/" + name + "/" + name + ".css");

				$(".navbar-themed").removeClass("navbar-dark navbar-light bg-primary bg-dark bg-light");

				for (var clsid in data.theme_classes) {
					$(".navbar-themed").addClass(data.theme_classes[clsid]);
				}

				setTimeout(function() {
					$("body").css('display', 'block');
					set_body_padding();
				}, 100);
			});

			$user.theme = name;
		});
	},
};

var $click = {

	bind: function(selector) {
		var self = this;
		if (selector) { selector = selector + ' '; } else { selector = ''; }

		$(selector + "[data-click]").click(function (e) {
			e.preventDefault();
			e.stopPropagation();
			self[$(this).data('click')](e);
		});
	},

	search: function() {
		if ($config.search) {
			if ($dir.mode != 'shares') {
				$mdl.draw('search').show();
			}
		}
	},

	mkdir: function() {
		if ($dir.mode == 'dir') {
			$mdl.draw('mkdir').show();
		}
	},

	settings: function() {
		if ($config.userdata) {
			$settings.modal();
		}
	},

	upload: function() {
		if ($dir.mode == 'dir') {
			$('#upload-i').trigger('click');
		} else {
			$err.show("Cannot upload", "You must navigate to a directory to upload files");
		}
	},

	shortcuts: function() {
		$mdl.draw('shortcuts').show();
	},

	mobile: function() {
		$mdl.draw('mobile').show();
	},

	about: function() {
		$mdl.draw('about').show();
	},

	connect: function() {
		if ($config.connect) {
			$mdl.draw('connect').show();
		}
	},

	bmark: function() {
		if ($dir.data.bmark) {
			if ($dir.mode == 'dir') {
				$mdl.draw('bmark', {name: $dir.data.bmark_path}).show();
			}
		}
	},

	layout: function() {
		if ($dir.mode != 'search') {
			newLayout = "list";
			if ($user.layout == "list") {
				newLayout = "grid";
			}
			$settings.layout(newLayout);
			$mdl.hide();
		}
	},

	parent: function() {
		if ($dir.mode == 'dir') {
			$dir.load($dir.epname, $dir.data.parent_path);
		}
	},

	dir: function(e) {
		$dir.load($dir.epname, get_path($(e.currentTarget)));
	},

	share: function(e) {
		this.dir(e);
	},

	root: function(e) {
		$dir.load($dir.epname, '');
	},

	file: function(e) {
		if ($user.click == 'ask') {
			$entry.action('properties', $(e.currentTarget), 'file');
			return;
		}

		if ($user.click == 'default' && $(e.currentTarget).data('view')) {
			window.open(get_url($(e.currentTarget), 'view'), '_blank');
			return;
		}

		window.location.href = get_url($(e.currentTarget), 'download');
	},
};

var $entry = {
	bind: function(selector) {
		var self = this;
		if (selector) { selector = selector + ' '; } else { selector = ''; }

		$(selector + '[data-entry]').click(function (e) {
			e.preventDefault();
			$entry[$(this).data('entry')](e);
		});
	},

	action: function(action, entry, type) {
		this.entry = entry;
		this.name = this.entry.data('name');

		if (this.entry.data('parent')) {
			this.path = this.entry.data('parent');
		} else {
			this.path = $dir.path;
		}

		this.type = type;
		this[action]();
	},

	rename: function(e) {
		$mdl.draw('rename', {name: this.name}).show();
	},

	delete: function() {
		$mdl.draw('delete', {name: this.name, type: this.type}).show();
	},

	copy: function() {
		$mdl.draw('copy', {name: 'Copy of ' + this.name}).show();
	},

	properties: function() {
		f = this.entry;
		data = {name: this.name, 
			size: f.data('size'),
			mtime: f.data('mtime'),
			atime: f.data('atime'),
			mtype: f.data('mtype'),
			icon: f.data('icon'),
			download: get_url(f, 'download'),
		};

		if (f.data('img')) {
			data.img = get_url(f, 'preview');
		}
		if (f.data('view')) {
			data.view = get_url(f, 'view');
		}

		$mdl.draw('file', data ).show();

		$.getJSON('/xhr/stat/' + $dir.epname + '/' + get_path(this.entry))
		.done(function(data) {
			if (data.code != 0) {
				$('.f-user').html('Unknown');
				$('.f-group').html('Unknown');
			} else {
				$('.f-user').html(data.owner);
				$('.f-group').html(data.group);
			}
		})
		.fail(function(jqXHR, textStatus, errorThrown) {
			$('.f-user').html('Unknown');
			$('.f-group').html('Unknown');
		});
	}
};

function init(epname, epurl, path) {
	/* load settings via ajax call */
	$.getJSON('/xhr/data')
	.fail(function(jqXHR, textStatus, errorThrown) {
		$err.fail("Unable to load settings", "Unable to contact the server", jqXHR, textStatus, errorThrown);
	})
	.done(function(data) {
		if (data.code !== 0) {
			$err.nonzero("Unable to load settings", data.msg, data.code);
		} else {
			$user = data.user;
			$config = data.config;

			set_body_padding();

			$( window ).resize(function() {
			  set_body_padding();
			});

			$click.bind();
			$fsub.bind();

			if (epname !== undefined) {
				env = nunjucks.configure('',{ autoescape: true});
				env.addFilter('filesizeformat', filesizeformat);
				env.addFilter('ts2str', ts2str);

				$settings.set_layout_cls();

				/* Activate tooltips and enable hiding on clicking */
				$('[data-tooltip="yes"]').tooltip({"delay": { "show": 600, "hide": 100 }, "placement": "bottom", "trigger": "hover"});
				$('[data-tooltip="yes"]').on('mouseup', function () {$(this).tooltip('hide');});

				/* respond to back/forward buttons */
				window.addEventListener('popstate', function(e) {
					if (e.state != null) {
						$dir.load(e.state.epname, e.state.path, false);
					}
				});

				/* File uploads - drag files over shows a modal */
				$('body').on('dragenter', function(e) {
					dt = e.originalEvent.dataTransfer;
					if (dt.types && (dt.types.indexOf ? dt.types.indexOf('Files') != -1 : dt.types.contains('Files'))) {
						dragCounter++;

						// only draw/show once, for the first drag event.
						if (dragCounter === 1) {
							$mdl.draw('drag').show().lg();
						}
					}
				});

				$('body').on('dragleave', function(e) {
					if (dragCounter > 0) {
						dragCounter--;
					}
					if (dragCounter === 0) {
						$mdl.hide();
					}
				});

				Mousetrap.bind('alt+up', function(e) {
					e.preventDefault();
					if ($dir.data.parent) {
						$mdl.hide(); $click.parent();
					}
				});

				Mousetrap.bind('shift+p', function(e) { e.preventDefault(); $click.settings(); });
				Mousetrap.bind('shift+s', function(e) { e.preventDefault(); $click.search(); });
				Mousetrap.bind('shift+n', function(e) { e.preventDefault(); $click.mkdir(); });
				Mousetrap.bind('shift+l', function(e) { e.preventDefault(); $click.layout(); });
				Mousetrap.bind('shift+u', function(e) { e.preventDefault(); $click.upload(); });
				Mousetrap.bind('shift+c', function(e) { e.preventDefault(); $click.connect(); });
				Mousetrap.bind('shift+b', function(e) { e.preventDefault(); $click.bmark(); });

				init_url = epurl + '/browse/' + path;
				history.replaceState({epurl: epurl, epname: epname, path: path}, '', init_url);
				$dir.load(epname, path, false);
			}
		}
	});
}

/* context (right click) menus */
(function ($, window) {
	$.fn.contextMenu = function (opts) {
		return this.each(function () {
			$(this).on("contextmenu", function (e) {
				if (e.ctrlKey) return;

				// Hide other menu type
				$(opts.hideSelector).removeClass('d-block');

				menu = $(opts.menu);
				menu.data('invokedOn', $(e.target))
				.css({
					position: "absolute",
					left: getMenuPosition(e.clientX, 'width', 'scrollLeft'),
					top: getMenuPosition(e.clientY, 'height', 'scrollTop')
				})
				.addClass("d-block")
				.off('click').on('click', 'a', function (e) {
					menu.removeClass('d-block');
					opts.func.call(this, menu.data('invokedOn'), $(e.target));
				});

				/* Extra code to show/hide view option based on type */
				if (menu.data('invokedOn').closest('[data-click="file"]').attr('data-view')) {
					$('#ctx-menu-view').removeClass('d-none').addClass('d-block');
				}
				else {
					$('#ctx-menu-view').removeClass('d-block').addClass('d-none');
				}

				return false;
			});

			//make sure menu closes on any click
			$('body').click(function () {
				$(opts.menu).removeClass('d-block');
			});
		});

		function getMenuPosition(mouse, direction, scrollDir) {
			var win = $(window)[direction](), scroll = $(window)[scrollDir](), menu = $(opts.menu)[direction](), position = mouse + scroll;

			// opening menu would pass the side of the page
			if (mouse + menu > win && menu < mouse) {
				position -= menu;
			}

			return position;
		}
	};
})(jQuery, window);
