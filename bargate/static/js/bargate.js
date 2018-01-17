var $user = {hidden: false, overwrite: false, twostep: false};
var $dir = {btnsEnabled: false, bmarkEnabled: false, sortBy: 'name' };
var dragTimerShow;
var dragCounter = 0;

function showErr(title,desc) {
	closeModals();
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

function openModal(name) {
	closeModals();
	$(name).modal('show');
}

function openDirModal(name) {
	if ($dir.btnsEnabled === true) {
		closeModals();
		$(name).modal('show');
	}
}

function closeModals() {
	open = $('.modal.show').attr('id'); 
	if (open) {
		$('#' + open).modal('hide');
	}
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

function enableBrowseButts() {
	$dir.btnsEnabled = true;
	$('.browse-b').attr("disabled", false).removeClass("disabled");
}

function disableBrowseButts() {
	$dir.btnsEnabled = false;
	$('.browse-b').attr("disabled", true).addClass("disabled");
}

function enableBmark() {
	$dir.bmarkEnabled = true;
	$('#bmark-l').removeClass('disabled');
	$('.bmark-b').attr("disabled", false).removeClass("disabled");
}

function disableBmark() {
	$dir.bmarkEnabled = false;
	$('#bmark-l').addClass('disabled');
	$('.bmark-b').attr("disabled", true).addClass("disabled");
}

function drawDir() {
	$('#pdiv').html(nunjucks.render('breadcrumbs.html', { crumbs: $dir.data.crumbs, root_name: $dir.data.root_name }));

	if ($dir.data.no_items) {
		$('#pdiv').append(nunjucks.render('empty.html'));
	} else {
		$('#pdiv').append(nunjucks.render('directory-' + $user.layout + '.html', {dirs: $dir.data.dirs, files: $dir.data.files, shares: $dir.data.shares, buildurl: buildurl}));
	}

	if ($user.layout == "list") {
		draw_list();
	}
	else {
		draw_grid();
	}

	doBrowse();
}

function reloadDir() {
	loadDir($dir.epname, $dir.path, false);
}

function loadDir(epname, path, alterHist) {
	if (alterHist === undefined) { alterHist = true; }

	$.getJSON('/xhr/ls/' + epname + '/' + path)
	.done(function(data) {
		if (data.code > 0) {
			raiseNonZero("Unable to open directory", data.msg, data.code);
		} else {
			if (data.bmark) {
				enableBmark();
			} else {
				disableBmark();
			}

			if (data.buttons) {
				enableBrowseButts();
			} else {
				disableBrowseButts();
			}

			$dir.data = data;
			$dir.epurl = data.epurl;
			$dir.epname = epname;
			$dir.path  = path;

			drawDir();
			prepFileUpload();

			if (alterHist) {
				new_url = data.epurl + '/browse/' + path;
				history.pushState({epname: epname, epurl: data.epurl, path: path}, '', new_url);
			}
		}
	})
	.fail(function(jqXHR, textStatus, errorThrown) {
		raiseFail("Unable to open folder", "Could not load folder contents", jqXHR, textStatus, errorThrown);
	});
}

function fsub_search() {
	$.getJSON('/xhr/search/' + $dir.epname + '/' + $dir.path, {q: $('#search-i').val()})
	.done(function(data) {
		if (data.code > 0) {
			raiseNonZero("Search failed", data.msg, data.code);
		} else {
			$dir.data = data;
			$dir.parent = false;
			$dir.parent_path = null;

			disableBmark();
			disableBrowseButts();

			$('#pdiv').html(nunjucks.render('search.html', data));

			draw_list();

			$('#results').DataTable( {
				"paging": false,
				"searching": false,
				"info": false,
				"ordering": false,
				"dom": 'lrtip'
			});

			doBrowse();
		}
	})
	.fail(function(jqXHR, textStatus, errorThrown) {
		raiseFail("Unable to search", "Could not obtain search results", jqXHR, textStatus, errorThrown);
	});
}

function click_layout() {
	if ($user.layout == "list") {
		newLayout = "grid";
	}
	else {
		newLayout = "list";
	}

	set_layout(newLayout);
	closeModals();
}


function bytes2str(bytes,decimals) {
	if (bytes == 0) return '0 Bytes';
	var sizes = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
	var i = Math.floor(Math.log(bytes) / Math.log(1024));
	return parseFloat((bytes / Math.pow(1024, i)).toFixed(1)) + ' ' + sizes[i];
}

function draw_list() {
	function nameToNum (by) {
		if (by == 'name') { return [4, "asc"]; }
		else if (by == 'mtime') { return [5, "asc"]; }
		else if (by == 'type') { return [6, "asc"]; }
		else if (by == 'size') { return [7, "asc"]; }
	}

	$("[data-sort]").on('click', function(e) {
		e.preventDefault();
		sortby = $(this).data('sort');
		$dir.sortBy = sortby;
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
		"order": [nameToNum($dir.sortBy)],
		"dom": 'lrtip'
	});
}

function doBrowse() {
	$("#pdiv .edir, .eshare").click(function(e) {
		e.preventDefault();
		loadDir( $dir.epname, $(this).data('path') );
	});

	$("#pdiv [data-click]").click(function (e) {
		e.preventDefault();
		window["click_" + $(this).data('click')]();
	});

	// Bind actions to buttons in the 'file show' modal
	$(".e-rename-b").click(function () { showRename(); });
	$(".e-copy-b").click(function () { showCopy(); });
	$(".e-delete-b").click(function () { showDeleteFile(); });

	/* What to do when a user clicks a file entry in a listing */
	$("#pdiv .efile").click(function() {
		if ($user.onclick == 'ask') {
			showFileOverview($(this));
		} else if ($user.onclick == 'default') {
			if ($(this).attr('data-view')) {
				window.open(buildurl($(this).data('path'), 'view'),'_blank');
			} else {
				window.open(buildurl($(this).data('path'), 'download'),'_blank');
			}
		} else {
			window.open(buildurl($(this).data('path'), 'download'),'_blank');
		}
	});

	/* right click menu for files */
	$(".efile").contextMenu({
		menuSelector: "#ctx-menu-file",
		hideSelector: "#ctx-menu-dir",
		menuSelected: function (item, selectedMenu)
		{
			file = item.closest(".efile");
			action = selectedMenu.closest("a").data("action");

			if (action == 'view' || action == 'download') {
				window.open(buildurl(file.data('path'),action),'_blank');
			}
			else if (action == 'copy') {
				selectEntry(file.data('filename'), $dir.path);
				showCopy();
			}
			else if (action == 'rename') {
				selectEntry(file.data('filename'), $dir.path);
				showRename();
			}
			else if (action == 'delete') {
				selectEntry(file.data('filename'), $dir.path);
				showDeleteFile();
			}
			else if (action == 'properties') {
				showFileOverview(file);
			}
		}
	});

	/* context menu for directories */
	$(".edir").contextMenu({
		menuSelector: "#ctx-menu-dir",
		hideSelector: "#ctx-menu-file",
		menuSelected: function (invokedOn, selectedMenu) {
			dir = invokedOn.closest(".edir");
			action = selectedMenu.closest("a").data("action");

			if (action == 'open') {
				loadDir($dir.epname, dir.data('path'));
			}
			else if (action == 'rename') {
				selectEntry(dir.data('filename'), $dir.path);
				showRename(dir.data('filename'));
			}
			else if (action == 'delete') {
				selectEntry(dir.data('filename'), $dir.path);
				showDeleteDirectory(dir.data('filename'));
			}
		}
	});
}

function draw_grid() {
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
		sortBy: $dir.sortBy,
	});

	$("[data-sort]").on('click', function(e) {
		e.preventDefault();
		sortby = $(this).data('sort');
		$dir.sortBy = sortby;
		$container.isotope({ sortBy: sortby });
		$('[data-sort] > span').addClass('d-none');
		$('[data-sort="' + sortby + '"] > span').removeClass('d-none');
	});

	var $dirs = $('#dirs').isotope( {
		getSortData: { name: '[data-sortname]',},
		sortBy: 'name',
	});
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

function prepFileUpload() {
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

					reloadDir();
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

function selectEntry(name, path) {
	$dir.entry = name;
	$dir.entryDirPath = path;
}

function buildurl(path, action) {
	return $dir.epurl + "/" + action + "/" + path;
}

function showFileOverview(file) {
	$('.file-m-owner').html('<span class="text-muted">Loading <span class="fas fa-spin fa-cog"></span></span>');
	$('.file-m-group').html('<span class="text-muted">Loading <span class="fas fa-spin fa-cog"></span></span>');

	$('.file-m-name').text(file.data('filename'));
	$('.file-m-size').text(file.data('size'));
	$('.file-m-mtime').text(ts2str(file.data('mtime')));
	$('.file-m-atime').text(ts2str(file.data('atime')));
	$('.file-m-mtype').text(file.data('mtype'));
	$('.file-m-icon').addClass(file.data('icon'));
	$('.file-m-download').attr('href',buildurl(file.data('path'), 'download'));

	if (file.attr('data-img')) {
		$('#file-m-preview').attr('src',buildurl(file.data('path'), 'preview')).removeClass('d-none');
	}
	else {
		$('#file-m-preview').attr('src','about:blank').addClass('d-none');
	}
	
	if (file.attr('data-view')) {
		$('.file-m-view').attr('href',buildurl(file.data('path'), 'view')).removeClass('d-none');
	}
	else {
		$('.file-m-view').addClass('d-none');
	}

	if (file.attr('data-parent')) {
		selectEntry(file.data('filename'), file.data('parent'));
	} else {
		selectEntry(file.data('filename'), $dir.path);
	}

	$('#file-m').modal('show');

	$.getJSON('/xhr/stat/' + $dir.epname + '/' + file.data('path'))
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

function showRename() {
	$('#e-rename-i').val($dir.entry);
	$('#e-rename-m').modal('show');
}

function showCopy() {
	$('#e-copy-i').val("Copy of " + $dir.entry);
	$('#e-copy-m').modal('show');
}

function showDeleteFile() {
	$('#e-delete-t').text("file");
	$('#e-delete-w').addClass('d-none');
	showDelete();
}

function showDeleteDirectory() {
	$('#e-delete-t').text("directory");
	$('#e-delete-w').removeClass('d-none');
	showDelete();
}

function showDelete() {
	$('#e-delete-n').text($dir.entry);
	$('#e-delete-m').modal('show');
}

function notifyOK(msg) {
	$.notify({ icon: 'fas fa-fw fa-check', message: msg },{ type: 'success', template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

function notifyErr(msg) {
	$.notify({ icon: 'fas fa-fw fa-exclamation-triangle', message: msg },{ type: 'danger', delay: 10000, template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

function fsub_2step_enable() {
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
}

function fsub_2step_disable() {
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
}

function do_action(action, params, desc, callback) {
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
	if ($dir.entryDirPath === $dir.path) {
		reloadDir();
	} else {
		loadDir($dir.epname, $dir.EntryDirPath);
	}
}

function fsub_rename() {
	do_action('rename', {path: $dir.entryDirPath, old_name: $dir.entry, new_name: $('#e-rename-i').val()}, 'rename', function () { load_ctx(); });
}

function fsub_copy() {
	do_action('copy', {path: $dir.entryDirPath, src: $dir.entry, dest: $('#e-copy-i').val()}, 'copy file', function () { load_ctx(); });
}

function fsub_delete() {
	do_action('delete', {path: $dir.entryDirPath, name: $dir.entry}, 'delete', function () { load_ctx(); });
}

function fsub_mkdir() {
	do_action('mkdir', {path: $dir.path, name: $('#mkdir-i').val()}, 'create directory', function () { reloadDir(); });
}

function fsub_bmark() {
	do_action('bookmark', {path: $dir.path, name: $('#bmark-i').val()}, 'create bookmark', function (data) { 
		$('.bmarks').append('<li><a href="' + data.url + '"><i class="fas fa-arrow-right fa-fw"></i>' + $('#bmark-i').val() + '</a></li>');
	});
}

function fsub_connect() {
	do_action('connect', {path: $('#connect-i').val()}, 'connect to server', function () { loadDir('custom', ''); });
}

function set_layout_cls() {
	if ($user.layout == "grid") {
		$("#pdiv").removeClass("listview").addClass("gridview");
		$(".layout-ico").removeClass("fa-th-large").addClass("fa-list");
	} else {
		$("#pdiv").removeClass("gridview").addClass("listview");
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
		drawDir();
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

function click_search() {
	openDirModal('#search-m');
}

function click_mkdir() {
	openDirModal('#mkdir-m');
}

function click_settings() {
	openModal('#prefs-m');
}

function click_upload() {
	openModal('#upload-m');
}

function click_shortcuts() {
	openModal('#shortcuts-m');
}

function click_mobile() {
	openModal('#mobile-m');
}

function click_about() {
	openModal('#about-m');
}

function click_connect() {
	contents = $('#connect-i').val();
	$('#connect-i').focus().val("").val(contents);
	openModal('#connect-m');
}

function click_bmark() {
	if ($dir.bmarkEnabled === true) {
		openDirModal('#bmark-m');
	}
}

function click_parent() {
	loadDir($dir.epname, $dir.data.parent_path);
}

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
					if ($dir.btnsEnabled) {
						reloadDir();
					}
					$user.hidden = show_hidden;
				});
			});

			$('input[type=radio][name=prefs-click-i]').change(function() {
				save_setting('click', this.value, function (data) { 
					if ($dir.btnsEnabled) {
						reloadDir();
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
				if ($(this).data('cmod') !== 'no') {
					closeModals();
				}

				window["fsub_" + $(this).data('fsub')]();
			});

			/* trigger js functions on click */
			$("[data-click]").click(function (e) {
				e.preventDefault();
				window["click_" + $(this).data('click')]();
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
						loadDir(e.state.epname, e.state.path, false);
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
						closeModals(); click_parent();
					}
				});

				Mousetrap.bind('shift+p', function(e) { e.preventDefault(); click_settings(); });
				Mousetrap.bind('shift+s', function(e) { e.preventDefault(); click_search(); });
				Mousetrap.bind('shift+n', function(e) { e.preventDefault(); click_mkdir(); });
				Mousetrap.bind('shift+l', function(e) { e.preventDefault(); click_layout(); });
				Mousetrap.bind('shift+u', function(e) { e.preventDefault(); click_upload(); });
				Mousetrap.bind('shift+c', function(e) { e.preventDefault(); click_connect(); });
				Mousetrap.bind('shift+b', function(e) { e.preventDefault(); click_bmark(); });

				init_url = epurl + '/browse/' + path;
				history.replaceState({epurl: epurl, epname: epname, path: path}, '', init_url);
				loadDir(epname, path, false);
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

				menu = $(opts.menuSelector);
				menu.data("invokedOn", $(e.target))
				.css({
					position: "absolute",
					left: getMenuPosition(e.clientX, 'width', 'scrollLeft'),
					top: getMenuPosition(e.clientY, 'height', 'scrollTop')
				})
				.addClass("d-block")
				.off('click').on('click', 'a', function (e) {
					menu.removeClass('d-block');
					opts.menuSelected.call(this, menu.data("invokedOn"), $(e.target));
				});

				/* Extra code to show/hide view option based on type */
				if (menu.data("invokedOn").closest(".efile").attr('data-view')) {
					$('#ctx-menu-view').removeClass('d-none').addClass('d-block');
				}
				else {
					$('#ctx-menu-view').removeClass('d-block').addClass('d-none');
				}

				return false;
			});

			//make sure menu closes on any click
			$('body').click(function () {
				$(opts.menuSelector).removeClass('d-block');
			});
		});

		function getMenuPosition(mouse, direction, scrollDir) {
			var win = $(window)[direction](), scroll = $(window)[scrollDir](), menu = $(opts.menuSelector)[direction](), position = mouse + scroll;

			// opening menu would pass the side of the page
			if (mouse + menu > win && menu < mouse) {
				position -= menu;
			}

			return position;
		}
	};
})(jQuery, window);
