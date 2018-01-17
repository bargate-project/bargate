var $user = {hidden: false, overwrite: false, twostep: false};
var dragTimerShow;
var dragCounter = 0;

function showErr(title,desc) {
	close_modal();
	$("#err-m-t").text(title);
	$("#err-m-d").text(desc);
	$('#err-m').modal('show');
}

function raiseFail(title, message, jqXHR, textStatus, errorThrown) {
	if (jqXHR.status === 0) {
		reason = "a network error occured.";
	} else if (jqXHR.status === 400) {
		reason = "the server said 'Bad Request'";
	} else {
		reason = textStatus;
	}

	showErr(title, message + ": " + reason);
}

function raiseNonZero(title, message, code) {
	if (code == 401) {
		location.reload(true); // redirect to login
	} else {
		showErr(title, message);
	}
}

function close_modal() {
	open = $('.modal.show').attr('id'); 
	if (open) {
		$('#' + open).modal('hide');
	}
}

function open_modal(name) {
	close_modal();
	$(name).modal('show');
}

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
		$('#pdiv').html(nunjucks.render('breadcrumbs.html', { crumbs: this.data.crumbs, root_name: this.data.root_name }));

		if (this.data.no_items) {
			$('#pdiv').append(nunjucks.render('empty.html'));
		} else {
			$('#pdiv').append(nunjucks.render('directory-' + $user.layout + '.html', {dirs: this.data.dirs, files: this.data.files, shares: this.data.shares, buildurl: buildurl}));
		}

		if ($user.layout == "list") {
			this.draw_list();
		}
		else {
			this.draw_grid();
		}

		this.set_triggers();
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

	set_triggers: function() {
		$("#pdiv [data-click]").click(function (e) {
			e.preventDefault();
			e.stopPropagation();
			$click[$(this).data('click')](e);
		});

		/* right click menu for files */
		$('[data-ctx="file"]').contextMenu({
			menu: "#ctx-menu-file",
			hide: "#ctx-menu-dir",
			func: function (item, selectedMenu) {
				file = item.closest('[data-click="file"]');
				action = selectedMenu.closest("a").data("action");

				if (action == 'view' || action == 'download') {
					window.open(buildurl(file.data('path'),action),'_blank');
				}
				else if (action == 'properties') {
					$entry.action(action, file, 'file');
				}
			}
		});

		/* context menu for directories */
		$('[data-ctx="dir"]').contextMenu({
			menu: "#ctx-menu-dir",
			hide: "#ctx-menu-file",
			func: function (invokedOn, selectedMenu) {
				dir = invokedOn.closest('[data-click="dir"]');
				action = selectedMenu.closest("a").data("action");

				if (action == 'open') {
					$dir.load($dir.epname, dir.data('path'));
				} else {
					$entry.action(action, dir, 'dir');
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
				raiseNonZero("Unable to open directory", data.msg, data.code);
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
			raiseFail("Unable to open folder", "Could not load folder contents", jqXHR, textStatus, errorThrown);
		});
	},

	reload: function() {
		this.load(this.epname, this.path, false);
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
			window.clearTimeout(dragTimerShow);
			dragTimerShow = null;
			dragCounter = 0;
			$('#upload-drag-m').modal('hide');
			$('#upload-m').modal('hide');

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

function buildurl(path, action) {
	return $dir.epurl + "/" + action + "/" + path;
}

function notifyOK(msg) {
	$.notify({ icon: 'fas fa-fw fa-check', message: msg },{ type: 'success', template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

function notifyErr(msg) {
	$.notify({ icon: 'fas fa-fw fa-exclamation-triangle', message: msg },{ type: 'danger', delay: 10000, template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

function xhr_post(action, params, desc, callback) {
	params.epname = $dir.epname;
	params.action = action;
	params._csrfp_token = $user.token;

	$.post( '/xhr', params)
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Error", "Unable to " + desc, jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Unable to " + desc, data.msg, data.code);
			} else {
				notifyOK(data.msg);
				callback(data);
			}
		});
}

function load_ctx() {
	if ($entry.path === $dir.path) {
		$dir.reload();
	} else {
		$dir.load($dir.epname, $entry.path);
	}
}

var $form_submit = {

	rename: function() {
		xhr_post('rename', {path: $entry.path, old_name: $entry.name, new_name: $('#e-rename-i').val()}, 'rename', function () { load_ctx(); });
	},

	copy: function() {
		xhr_post('copy', {path: $entry.path, src: $entry.name, dest: $('#e-copy-i').val()}, 'copy file', function () { load_ctx(); });
	},

	delete: function() {
		xhr_post('delete', {path: $entry.path, name: $entry.name}, 'delete', function () { load_ctx(); });
	},

	mkdir: function() {
		xhr_post('mkdir', {path: $dir.path, name: $('#mkdir-i').val()}, 'create directory', function () { $dir.reload(); });
	},

	bmark: function() {
		xhr_post('bookmark', {path: $dir.path, name: $('#bmark-i').val()}, 'create bookmark', function (data) { 
			$('.bmarks').append('<li><a href="' + data.url + '"><i class="fas fa-arrow-right fa-fw"></i>' + $('#bmark-i').val() + '</a></li>');
		});
	},

	connect: function() {
		xhr_post('connect', {path: $('#connect-i').val()}, 'connect to server', function () { $dir.load('custom', ''); });
	},

	search: function() {
		$.getJSON('/xhr/search/' + $dir.epname + '/' + $dir.path, {q: $('#search-i').val()})
		.done(function(data) {
			if (data.code > 0) {
				raiseNonZero("Search failed", data.msg, data.code);
			} else {
				$dir.data = data;

				$dir.mode = "search";
				$('.b-dir').attr("disabled", true).addClass("disabled");
				$('.b-layout').attr("disabled", true).addClass("disabled");
				$('[data-click="bmark"]').addClass('disabled');

				$('#pdiv').html(nunjucks.render('search.html', data));

				$('#results').DataTable({
					"paging": false,
					"searching": false,
					"info": false,
					"ordering": false,
					"dom": 'lrtip'
				});

				$dir.set_triggers();
			}
		})
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Unable to search", "Could not obtain search results", jqXHR, textStatus, errorThrown);
		});
	},

	totp_enable: function() {
		$.post( '/2step/enable', { _csrfp_token: $user.token, token: $('#twostep-enable-i').val()})
			.fail(function(jqXHR, textStatus, errorThrown) {
				raiseFail("Network error", "Could not enable two-step verification", jqXHR, textStatus, errorThrown);
			})
			.done(function(data, textStatus, jqXHR) {
				if (data.code !== 0) {
					raiseNonZero("Unable to enable two-step verification", data.msg, data.code);
				} else {
					$('.twoStepDisabled').addClass('d-none');
					$('.twoStepEnabled').removeClass('d-none');
					if ($user.twostep.trusted) {
						$('.twoStepTrusted').removeClass('d-none');
						$('.twoStepUntrusted').addClass('d-none');
					} else {
						$('.twoStepTrusted').addClass('d-none');
						$('.twoStepUntrusted').removeClass('d-none');
					}
					$('#twostep-enable-i').val('');
					$('#twostep-disable-i').val('');
				}
		});
	},

	totp_disable: function() {
		$.post( '/2step/disable', { _csrfp_token: $user.token, token: $('#twostep-disable-i').val()})
			.fail(function(jqXHR, textStatus, errorThrown) {
				raiseFail("Network error", "Could not disable two-step verification", jqXHR, textStatus, errorThrown);
			})
			.done(function(data, textStatus, jqXHR) {
				if (data.code !== 0) {
					raiseNonZero("Unable to disable two-step verification", data.msg, data.code);
				} else {
					$('.twoStepEnabled').addClass('d-none');
					$('.twoStepDisabled').removeClass('d-none');
					$('#twostep-enable-i').val('');
					$('#twostep-disable-i').val('');
				}
		});
	},

};

function set_layout_cls() {
	if ($user.layout == "grid") {
		$(".layout-ico").removeClass("fa-th-large").addClass("fa-list");
	} else {
		$(".layout-ico").removeClass("fa-list").addClass("fa-th-large");
	}
}

function save_setting(key, value, callback) {
	$.post( "/xhr/settings", { key: key, value: value, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Settings error", "Unable to save settings", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Settings error", data.msg, data.code);
			} else {
				callback(data);
			}
		});
}

function set_layout(newLayout) {
	save_setting('layout', newLayout, function (data) { 
		$user.layout = newLayout;
		set_layout_cls();
		$dir.draw();
	});

}

function set_theme(themeName) {
	if (themeName == $user.theme) { return; }

	save_setting('theme', themeName, function (data) { 
		$("body").fadeOut(100, function() {
			$("body").css('display', 'none');
			$("#theme-l").attr("href", "/static/themes/" + themeName + "/bootstrap.min.css");
			$("#theme-o-l").attr("href", "/static/themes/" + themeName + "/" + themeName + ".css");

			$(".navbar-themed").removeClass("navbar-dark").removeClass("navbar-light").removeClass("bg-primary").removeClass("bg-dark").removeClass("bg-light");

			for (var clsid in data.theme_classes) {
				$(".navbar-themed").addClass(data.theme_classes[clsid]);
			}

			setTimeout(function() {
				$("body").css('display', 'block');
			}, 100);
		});

		$user.theme = themeName;
	});
}

var $click = {

	search: function() {
		if ($dir.mode != 'shares') {
			open_modal('#search-m');
		}
	},

	mkdir: function() {
		if ($dir.mode == 'dir') {
			open_modal('#mkdir-m');
		}
	},

	settings: function() {
		open_modal('#prefs-m');
	},

	upload: function() {
		if ($dir.mode == 'dir') {
			open_modal('#upload-m');
		}
	},

	shortcuts: function() {
		open_modal('#shortcuts-m');
	},

	mobile: function() {
		open_modal('#mobile-m');
	},

	about: function() {
		open_modal('#about-m');
	},

	connect: function() {
		contents = $('#connect-i').val();
		$('#connect-i').focus().val("").val(contents);
		open_modal('#connect-m');
	},

	bmark: function() {
		if ($dir.data.bmark === true) {
			if ($dir.mode == 'dir') {
				open_modal('#bmark-m');
			}
		}
	},

	layout: function() {
		if ($dir.mode != 'search') {
			newLayout = "list";
			if ($user.layout == "list") {
				newLayout = "grid";
			}

			set_layout(newLayout);
			close_modal();
		}
	},

	parent: function() {
		if ($dir.mode == 'dir') {
			$dir.load($dir.epname, $dir.data.parent_path);
		}
	},

	dir: function(e) {
		$dir.load( $dir.epname, $(e.currentTarget).data('path') );
	},

	share: function(e) {
		$dir.load( $dir.epname, $(e.currentTarget).data('path') );
	},

	file: function(e) {
		if ($user.onclick == 'ask') {
			$entry.action('properties', $(e.currentTarget), 'file');
			return;
		}

		if ($user.onclick == 'default' && $(e.currentTarget).data('view')) {
			window.open(buildurl($(e.currentTarget).data('path'), 'view'),'_blank');
			return;
		}

		window.open(buildurl($(e.currentTarget).data('path'), 'download'),'_blank');
	},
};

var $entry = {

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
		$('#e-rename-i').val(this.name);
		open_modal('#e-rename-m');
	},

	delete: function() {
		$('#e-delete-n').text(this.name);

		if (this.type == 'dir') {
			$('#e-delete-t').text("directory");
			$('#e-delete-w').removeClass('d-none');
		} else {
			$('#e-delete-t').text("file");
			$('#e-delete-w').addClass('d-none');
		}
		open_modal('#e-delete-m');
	},

	copy: function() {
		$('#e-copy-i').val("Copy of " + this.name);
		open_modal('#e-copy-m');
	},

	properties: function() {
		$('.file-m-owner').html('<span class="text-muted">Loading <span class="fas fa-spin fa-cog"></span></span>');
		$('.file-m-group').html('<span class="text-muted">Loading <span class="fas fa-spin fa-cog"></span></span>');

		$('.file-m-name').text(this.name);
		$('.file-m-size').text(this.entry.data('size'));
		$('.file-m-mtime').text(ts2str(this.entry.data('mtime')));
		$('.file-m-atime').text(ts2str(this.entry.data('atime')));
		$('.file-m-mtype').text(this.entry.data('mtype'));
		$('.file-m-icon').addClass(this.entry.data('icon'));
		$('.file-m-download').attr('href',buildurl(this.entry.data('path'), 'download'));

		if (this.entry.attr('data-img')) {
			$('#file-m-preview').attr('src',buildurl(this.entry.data('path'), 'preview')).removeClass('d-none');
		}
		else {
			$('#file-m-preview').attr('src','about:blank').addClass('d-none');
		}
		
		if (this.entry.data('view')) {
			$('.file-m-view').attr('href',buildurl(this.entry.data('path'), 'view')).removeClass('d-none');
		}
		else {
			$('.file-m-view').addClass('d-none');
		}

		open_modal('#file-m');

		$.getJSON('/xhr/stat/' + $dir.epname + '/' + this.entry.data('path'))
		.done(function(data) {
			if (data.code != 0) {
				$('.file-m-owner').html('Unknown');
				$('.file-m-group').html('Unknown');
			} else {
				$('.file-m-owner').html(data.owner);
				$('.file-m-group').html(data.group);
			}
		})
		.fail(function(jqXHR, textStatus, errorThrown) {
			$('.file-m-owner').html('Unknown');
			$('.file-m-group').html('Unknown');
		});
	}
};

function init(epname, epurl, path) {
	/* load settings via ajax call */
	$.getJSON('/xhr/settings')
	.fail(function(jqXHR, textStatus, errorThrown) {
		raiseFail("Unable to load settings", "Unable to contact the server", jqXHR, textStatus, errorThrown);
	})
	.done(function(data) {
		if (data.code !== 0) {
			raiseNonZero("Unable to load settings", data.msg, data.code);
		} else {
			$user = data;

			/* Load the preferences into the prefs modal */
			$('#prefs-m').on('show.bs.modal', function() {
				$('#prefs-layout-' + $user.layout).attr("checked", true);
				if ($user.hidden === true) {
					$('#prefs-hidden').attr("checked", true);
				}
				$('#prefs-click-' + $user.onclick).attr("checked",true);
				if ($user.overwrite === true) {
					$('#prefs-overwrite').attr("checked",true);
				}
				$('#prefs-theme-' + $user.theme).attr("checked",true);

				if ($user.totp.enabled === true) {
					$('.twoStepEnabled').removeClass('d-none');
					$('.twoStepDisabled').addClass('d-none');

					if ($user.totp.trusted === true) {
						$('.twoStepTrusted').removeClass('d-none');
						$('.twoStepUntrusted').addClass('d-none');
					}
				} else {
					$('#qrcode').attr('src', $('#qrcode').data('src'));
				}
			});

			/* Set up actions when preferences are changed */
			$('input[type=radio][name=prefs-layout-i]').change(function() {
				set_layout(this.value);
			});

			$('#prefs-hidden').change(function() {
				save_setting('hidden', this.checked, function (data) { 
					if ($dir.mode == 'dir') {
						$dir.reload();
					}
					$user.hidden = show_hidden;
				});
			});

			$('input[type=radio][name=prefs-click-i]').change(function() {
				save_setting('click', this.value, function (data) { 
					if ($dir.mode == 'dir') {
						$dir.reload();
					}
					$user.onclick = newMode;
				});
			});

			$('#prefs-overwrite').change(function() {
				save_setting('overwrite', this.checked, function (data) { 
					$user.overwrite = overwrite;
				});
			});

			$('input[type=radio][name=prefs-theme-i]').change(function() {
				set_theme(this.value);
			});

			/* trigger js functions on form submissions */
			$("[data-fsub]").submit(function (e) {
				e.preventDefault();
				if ($(this).data('cmod') != 'no') {
					close_modal();
				}

				$form_submit[$(this).data('fsub')](e);
			});

			/* trigger js functions on click */
			$("[data-click]").click(function (e) {
				console.log("data-click handler: " + $(this).data('click'));
				e.preventDefault();
				e.stopPropagation();
				$click[$(this).data('click')](e);
			});

			if (epname !== undefined) {
				env = nunjucks.configure('',{ autoescape: true});
				env.addFilter('filesizeformat', filesizeformat);
				env.addFilter('ts2str', ts2str);

				set_layout_cls();

				/* Activate tooltips and enable hiding on clicking */
				$('[data-tooltip="yes"]').tooltip({"delay": { "show": 600, "hide": 100 }, "placement": "bottom", "trigger": "hover"});
				$('[data-tooltip="yes"]').on('mouseup', function () {$(this).tooltip('hide');});

				/* respond to back/forward buttons */
				window.addEventListener('popstate', function(e) {
					if (e.state != null) {
						$dir.load(e.state.epname, e.state.path, false);
					}
				});

				/* focus on inputs when modals open */
				$('.modal').on('shown.bs.modal', function() {
					$('.modal.show input.mfocus').focus();
				});

				$('#bmark-m').on('shown.bs.modal', function() {
					$('#bmark-m input[type="text"]').focus().val($dir.data.bmark_path);
				});

				/* File uploads - drag files over shows a modal */
				$('body').on('dragenter', function(e) {
					dt = e.originalEvent.dataTransfer;
					if (dt.types && (dt.types.indexOf ? dt.types.indexOf('Files') != -1 : dt.types.contains('Files'))) {
						dragCounter++;

						if (!dragTimerShow) {
							dragTimerShow = window.setTimeout(function() {
								open = $('.modal.in').attr('id');
								if (open) {
									if (open != 'upload-drag-m') {
										$('#' + open).modal('hide');
									}
								}
								$('#upload-drag-m').modal('show'); dragTimerShow = null;
							}, 200);
						}
					}
				});

				$("[data-entry]").click(function (e) {
					e.preventDefault();
					$entry[$(this).data('entry')](e);
				});

				$('body').on('dragleave', function(e) {
					if (dragCounter > 0) {
						dragCounter--;
					}
					if (dragCounter === 0) {
						window.clearTimeout(dragTimerShow);
						dragTimerShow = null;
						$('#upload-drag-m').modal('hide');
					}
				});

				Mousetrap.bind('alt+up', function(e) {
					e.preventDefault();
					if ($dir.data.parent) {
						close_modal(); $click.parent();
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
				menu.data("invokedOn", $(e.target))
				.css({
					position: "absolute",
					left: getMenuPosition(e.clientX, 'width', 'scrollLeft'),
					top: getMenuPosition(e.clientY, 'height', 'scrollTop')
				})
				.addClass("d-block")
				.off('click').on('click', 'a', function (e) {
					menu.removeClass('d-block');
					opts.func.call(this, menu.data("invokedOn"), $(e.target));
				});

				/* Extra code to show/hide view option based on type */
				if (menu.data("invokedOn").closest('[data-click="file"]').attr('data-view')) {
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
