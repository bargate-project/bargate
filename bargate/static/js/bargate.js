function showErr(title,desc) {
	closeModals();
	$("#modal-error-title").text(title);
	$("#modal-error-desc").text(desc);
	$('#modal-error').modal('show');
	event.preventDefault();
	event.stopPropagation();
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

function closeModals() {
	var openModal = $('.modal.in').attr('id'); 
	if (openModal) {
		$('#' + openModal).modal('hide');
	}
}

var $user = {layout: null, token: null, theme: null, navbar: null, hidden: false, overwrite: false, onclick: null};
var $browse = {epname: null, epurl: null, path: null, entry: null, entryDirPath: null, btnsEnabled: false, bmarkEnabled: false,
	sortBy: 'name', data: null,
};

function enableBrowseButts() {
	if ($browse.btnsEnabled === false) {
		$browse.btnsEnabled = true;
		$('.browse-b').attr("disabled", false);
		$('.browse-b').removeClass("disabled");
	}
}

function disableBrowseButts() {
	if ($browse.btnsEnabled === true) {
		$browse.btnsEnabled = false;
		$('.browse-b').attr("disabled", true);
		$('.browse-b').addClass("disabled");
	}
}

function enableBookmark() {
	if (!$browse.bmarkEnabled) {
		$browse.bmarkEnabled = true;
		$('#bmark-l').removeClass('disabled');
		$('.bmark-b').attr("disabled", false);
		$('.bmark-b').removeClass("disabled");
	}
}

function disableBookmark() {
	if ($browse.bmarkEnabled) {
		$browse.bmarkEnabled = false;
		$('#bmark-l').addClass('disabled');
		$('.bmark-b').attr("disabled", true);
		$('.bmark-b').addClass("disabled");
	}
}

function renderDirectory() {
	$('#browse').html(nunjucks.render('breadcrumbs.html', { crumbs: $browse.data.crumbs, root_name: $browse.data.root_name }));

	if ($browse.data.no_items) {
		$('#browse').append(nunjucks.render('empty.html'));
	} else {
		$('#browse').append(nunjucks.render('directory-' + $user.layout + '.html', {dirs: $browse.data.dirs, files: $browse.data.files, shares: $browse.data.shares, buildurl: buildurl}));
	}

	if ($user.layout == "list") {
		doListView();
	}
	else {
		doGridView();
	}

	doBrowse();
}

function reloadDir() {
	loadDir($browse.epname, $browse.path, false);
}

function loadDir(epname, path, alterHistory) {
	if (alterHistory === undefined) { alterHistory = true; }

	$.getJSON('/xhr/ls/' + epname + '/' + path)
	.done(function(response) {
		if (response.code > 0) {
			raiseNonZero("Unable to open directory", response.msg, response.code);
		} else {
			if (response.bmark) {
				enableBookmark();
			} else {
				disableBookmark();
			}

			if (response.buttons) {
				enableBrowseButts();
			} else {
				disableBrowseButts();
			}

			$browse.data = response;
			renderDirectory();
			prepFileUpload();

			if (alterHistory) {
				new_url = response.epurl + '/browse/' + path;
				history.pushState({epname: epname, epurl: response.epurl, path: path}, '', new_url);
			}
			$browse.epurl = response.epurl;
			$browse.epname = epname;
			$browse.path  = path;

		}
	})
	.fail(function(jqXHR, textStatus, errorThrown) {
		raiseFail("Unable to open folder", "Could not load folder contents", jqXHR, textStatus, errorThrown);
	});
}

function browseParent() {
	if ($browse.data.parent) {
		loadDir($browse.epname, $browse.data.parent_path);
	}
}

function doSearch() {
	$('#search-m').modal('hide');

	$.getJSON('/xhr/search/' + $browse.epname + '/' + $browse.path, {q: $('#search-i').val()})
	.done(function(response) {
		if (response.code > 0) {
			raiseNonZero("Search failed", response.msg, response.code);
		} else {
			$browse.data = response;
			$browse.parent = false;
			$browse.parent_path = null;

			disableBookmark();
			disableBrowseButts();

			$('#browse').html(nunjucks.render('search.html', response));

			doListView();

			$('#results').DataTable( {
				"paging": false,
				"searching": false,
				"info": false,
				"columns": [
					{ "orderable": false },
					{ "orderable": false },
				],
				"dom": 'lrtip'
			});

			doBrowse();
		}
	})
	.fail(function(jqXHR, textStatus, errorThrown) {
		raiseFail("Unable to search", "Could not obtain search results", jqXHR, textStatus, errorThrown);
	});
}

function switchLayout() {
	// work out the new layout
	if ($user.layout == "list") {
		newLayout = "grid";
	}
	else {
		newLayout = "list";
	}

	setLayoutMode(newLayout);
}


function bytesToString(bytes,decimals) {
	if (bytes == 0) return '0 Bytes';
	var sizes = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
	var i = Math.floor(Math.log(bytes) / Math.log(1024));
	return parseFloat((bytes / Math.pow(1024, i)).toFixed(1)) + ' ' + sizes[i];
}

function doListView() {
	/* sort entries in a directory */
	$('.dir-sortby-name').on( 'click', function()
	{
		$browse.sortBy = 'name';
		$('#dir').DataTable().order([3,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-name span').removeClass('invisible');
	});
	$('.dir-sortby-mtime').on( 'click', function()
	{
		$browse.sortBy = 'mtime';
		$('#dir').DataTable().order([4,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-mtime span').removeClass('invisible');
	});
	$('.dir-sortby-type').on( 'click', function()
	{
		$browse.sortBy = 'type';
		$('#dir').DataTable().order([5,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-type span').removeClass('invisible');
	});
	$('.dir-sortby-size').on( 'click', function()
	{
		$browse.sortBy = 'size';
		$('#dir').DataTable().order([6,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-size span').removeClass('invisible');
	});

	if ($browse.sortBy == 'name') { itemOrder = [3,"asc"]; }
	else if ($browse.sortBy == 'mtime') { itemOrder = [4,"asc"]; }
	else if ($browse.sortBy == 'type') { itemOrder = [5,"asc"]; }
	else if ($browse.sortBy == 'size') { itemOrder = [6,"asc"]; }

	$('#dir').DataTable( {
		"paging": false,
		"searching": false,
		"info": false,
		"columns": [
			{ "orderable": false },
			{ "orderable": false },
			{ "orderable": false },
			{ "visible": false},
			{ "visible": false},
			{ "visible": false},
			{ "visible": false},
		],
		"order": [itemOrder],
		"dom": 'lrtip'
	});
}

function doBrowse() {
	$(".edir").click(function() {
		loadDir( $browse.epname, $(this).data('path') );
		event.preventDefault();
		event.stopPropagation();
	});

	$(".eshare").click(function() {
		loadDir( $browse.epname, $(this).data('path') );
	});

	// Bind actions to buttons in the 'file show' modal
	$(".e-rename-b").click(function () { showRename(); });
	$(".e-copy-b").click(function () { showCopy(); });
	$(".e-delete-b").click(function () { showDeleteFile(); });

	/* What to do when a user clicks a file entry in a listing */
	$(".efile").click(function() {
		if ($user.onclick == 'ask') {
			showFileOverview($(this));
		} else if ($user.onclick == 'default') {
			if ($(this).attr('data-view')) {
				window.open(buildurl($(this).data('epurl'), $(this).data('path'), 'view'),'_blank');
			} else {
				window.open(buildurl($(this).data('epurl'), $(this).data('path'), 'download'),'_blank');
			}
		} else {
			window.open(buildurl($(this).data('epurl'), $(this).data('path'), 'download'),'_blank');
		}
	});

	/* right click menu for files */
	$(".efile").contextMenu({
		menuSelector: "#fileContextMenu",
		menuSelected: function (invokedOn, selectedMenu)
		{
			var file = invokedOn.closest(".efile");
			var $action = selectedMenu.closest("a").data("action");

			if ($action == 'view') {
				window.open(buildurl(file.data('epurl'), file.data('path'),'view'),'_blank');
			}
			else if ($action == 'download') {
				window.open(buildurl(file.data('epurl'), file.data('path'),'download'),'_blank');
			}
			else if ($action == 'copy') {
				selectEntry(file.data('filename'), $browse.path);
				showCopy();
			}
			else if ($action == 'rename') {
				selectEntry(file.data('filename'), $browse.path);
				showRename();
			}
			else if ($action == 'delete') {
				selectEntry(file.data('filename'), $browse.path);
				showDeleteFile();
			}
			else if ($action == 'properties') {
				showFileOverview(file);
			}

			event.preventDefault();
			event.stopPropagation();
		}
	});

	/* context menu for directories */
	$(".edir").contextMenu({
		menuSelector: "#dirContextMenu",
		menuSelected: function (invokedOn, selectedMenu) {
			var dir = invokedOn.closest(".edir");
			var $action = selectedMenu.closest("a").data("action");

			if ($action == 'open') {
				loadDir($browse.epname, dir.data('path'));
			}
			else if ($action == 'rename') {
				selectEntry(dir.data('filename'), $browse.path);
				showRename(dir.data('filename'));
			}
			else if ($action == 'delete') {
				selectEntry(dir.data('filename'), $browse.path);
				showDeleteDirectory(dir.data('filename'));
			}

			event.preventDefault();
			event.stopPropagation();
		}
	});
}

function doGridView() {
	var $container = $('#files').isotope({
		getSortData:
		{
			name: '[data-sortname]',
			type: '[data-mtyper]',
			mtime: '[data-mtimer] parseInt',
			size: '[data-sizer] parseInt',
		},
		transitionDuration: '0.2s',
		percentPosition: true,
		sortAscending:
		{
			name: true,
			type: true,
			mtime: false,
			size: false
		},
		sortBy: $browse.sortBy,
	});

	/* sort entries in a directory */
	$('.dir-sortby-name').on( 'click', function() {
		$browse.sortBy = 'name';
		$container.isotope({ sortBy: 'name' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-name span').removeClass('invisible');
	});
	$('.dir-sortby-mtime').on( 'click', function() {
		$browse.sortBy = 'mtime';
		$container.isotope({ sortBy: 'mtime' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-mtime span').removeClass('invisible');
	});
	$('.dir-sortby-type').on( 'click', function() {
		$browse.sortBy = 'type';
		$container.isotope({ sortBy: 'type' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-type span').removeClass('invisible');
	});
	$('.dir-sortby-size').on( 'click', function() {
		$browse.sortBy = 'size';
		$container.isotope({ sortBy: 'size' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-size span').removeClass('invisible');
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

function bitrateformat(bits) {
	var bytes = bits / 8;
	bytes = parseFloat(bytes);
	var units = ['Bytes/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s'];

	if (bytes === 1) {
		return '1 Byte/s';
	} else if (bytes < 1024) {
		return bytes + ' Bytes/s';
	} else {
		return units.reduce(function (match, unit, index) {
			var size = Math.pow(1024, index);
			if (bytes >= size) {
				return (bytes/size).toFixed(1) + ' ' + unit;
			}
			return match;
		});
	}
}

function prepFileUpload() {
	$('#upload-i').fileupload({
		url: '/xhr',
		dataType: 'json',
		maxChunkSize: 10485760, // 10MB
		formData: [{name: '_csrfp_token', value: $user.token}, {name: 'action', value: 'upload'}, {name: 'epname', value: $browse.epname}, {name: 'path', value: $browse.path}],
		stop: function (e, data) {
			window.uploadNotify.close();
			delete window.uploadNotify;
			if (window.numUploadsDone > 1) {
				notifySuccess(window.numUploadsDone + " files uploaded");
			}
		},
		done: function (e, data) {
			$.each(data.result.files, function (index, file) {
				if (file.error) {
					notifyError("Upload of '" + file.name + "' failed: " + file.error);
				}
				else {
					window.numUploadsDone = window.numUploadsDone + 1;
					if (window.numUploads == 1) {
						notifySuccess("Uploaded " + file.name);
					}

					reloadDir();
				}
			});
		},
		fail: function (e, data) {
			if (data.errorThrown != 'abort') {
				notifyError("Upload failed: " + data.errorThrown);
			}
		},
		progressall: function (e, data) {
			progress = parseInt(data.loaded / data.total * 100, 10);
			window.uploadNotify.update('progress', progress);
			window.uploadNotify.update('message', progress + "% " + filesizeformat(data.loaded) + ' out of ' + filesizeformat(data.total) + ", " + bitrateformat(data.bitrate));
		},
		add: function (e, data) {
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
					notifyError("Upload cancelled");
				} else {
					notifyError("Uploads cancelled");
				}
			});
		},
	}).prop('disabled', !$.support.fileInput).parent().addClass($.support.fileInput ? undefined : 'disabled');
}

function selectEntry(name, path) {
	$browse.entry = name;
	$browse.entryDirPath = path;
}

function buildurl(epurl, path, action) {
	return epurl + "/" + action + "/" + path;
}

function showFileOverview(file) {
	$('.file-m-owner').html('<span class="text-muted">Loading <span class="fas fa-spin fa-cog"></span></span>');
	$('.file-m-group').html('<span class="text-muted">Loading <span class="fas fa-spin fa-cog"></span></span>');

	$('.file-m-name').text(file.data('filename'));
	$('.file-m-size').text(file.data('size'));
	$('.file-m-mtime').text(file.data('mtime'));
	$('.file-m-atime').text(file.data('atime'));
	$('.file-m-mtype').text(file.data('mtype'));
	$('.file-m-icon').addClass(file.data('icon'));
	$('.file-m-download').attr('href',buildurl(file.data('epurl'), file.data('path'), 'download'));


	if (file.attr('data-img')) {
		$('#file-m-preview').attr('src',buildurl(file.data('epurl'), file.data('path'), 'preview'));
		$('#file-m-preview').removeClass('hidden');
	}
	else {
		$('#file-m-preview').attr('src','');
		$('#file-m-preview').addClass('hidden');
	}
	
	if (file.attr('data-view')) {
		$('.file-m-view').attr('href',buildurl(file.data('epurl'), file.data('path'), 'view'));
		$('.file-m-view').removeClass('hidden');
	}
	else {
		$('.file-m-view').addClass('hidden');
	}

	if (file.attr('data-parent')) {
		selectEntry(file.data('filename'),file.data('parent'));
	} else {
		selectEntry(file.data('filename'),$browse.path);
	}

	$('#file-m').modal('show');

	$.getJSON('/xhr/stat/' + $browse.epname + '/' + file.data('path'))
	.done(function(response) {
		if (response.code != 0) {
			$('.file-m-owner').html('Unknown');
			$('.file-m-group').html('Unknown');
		} else {
			$('.file-m-owner').html(response.owner);
			$('.file-m-group').html(response.group);
		}
	})
	.fail(function(jqXHR, textStatus, errorThrown) {
		$('.file-m-owner').html('Unknown');
		$('.file-m-group').html('Unknown');
	});
}

function showRename() {
	$('#e-rename-i').val($browse.entry);
	$('#e-rename-m').modal('show');
	$('#e-rename-i').focus();
}

function showCopy() {
	$('#e-copy-i').val("Copy of " + $browse.entry);
	$('#e-copy-m').modal('show');
	$('#e-copy-i').focus();
}

function showDeleteFile() {
	$('#e-delete-t').text("file");
	$('#e-delete-w').addClass("hidden");
	showDelete();
}

function showDeleteDirectory() {
	$('#e-delete-t').text("directory");
	$('#e-delete-w').removeClass("hidden");
	showDelete();
}

function showDelete() {
	$('#e-delete-n').text($browse.entry);
	$('#e-delete-m').modal('show');
}

function notifySuccess(msg) {
	$.notify({ icon: 'fas fa-fw fa-check', message: msg },{ type: 'success', template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

function notifyError(msg) {
	$.notify({ icon: 'fas fa-fw fa-exclamation-triangle', message: msg },{ type: 'danger', delay: 10000, template: nunjucks.render('notify.html'), placement: {align: 'center', from: 'bottom'}});
}

function doRename() {
	$('#e-rename-m').modal('hide');
	$.post( '/xhr', { epname: $browse.epname, path: $browse.entryDirPath, action: 'rename', _csrfp_token: $user.token, old_name: $browse.entry, new_name: $('#e-rename-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Unable to rename", "Could not rename", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Unable to rename", data.msg, data.code);
			} else {
				notifySuccess(data.msg);
				if ($browse.entryDirPath === $browse.path) {
					reloadDir();
				} else {
					loadDir($browse.epname, $browse.EntryDirPath);
				}
			}
	});
}

function doCopy() {
	$('#e-copy-m').modal('hide');
	$.post( '/xhr', { epname: $browse.epname, path: $browse.entryDirPath, action: 'copy', _csrfp_token: $user.token, src: $browse.entry, dest: $('#e-copy-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Unable to copy", "Could not copy file", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Unable to copy", data.msg, data.code);
			} else {
				notifySuccess(data.msg);
				if ($browse.entryDirPath === $browse.path) {
					reloadDir();
				} else {
					loadDir($browse.epname, $browse.entryDirPath);
				}
			}
	});
}

function doMkdir() {
	$('#mkdir-m').modal('hide');
	$.post( '/xhr', { epname: $browse.epname, path: $browse.path, action: 'mkdir', _csrfp_token: $user.token, name: $('#mkdir-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Unable to create directory", "Could not create directory", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Unable to create directory", data.msg, data.code);
			} else {
				notifySuccess(data.msg);
				reloadDir();
			}
	});
}

function doBookmark() {
	$('#bmark-m').modal('hide');
	bmarkName = $('#bmark-i').val();
	$.post( '/xhr', { epname: $browse.epname, path: $browse.path, action: 'bookmark', _csrfp_token: $user.token, name: bmarkName})
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Unable to create bookmark", "Could not create bookmark", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Unable to create bookmark", data.msg, data.code);
			} else {
				notifySuccess(data.msg);
				$('#bmarks').append('<li><a href="' + data.url + '"><i class="fas fa-arrow-right fa-fw"></i>' + bmarkName + '</a></li>');
			}
	});
}

function doDelete() {
	$('#e-delete-m').modal('hide');
	$.post( '/xhr', { epname: $browse.epname, path: $browse.entryDirPath, action: 'delete', _csrfp_token: $user.token, name: $browse.entry})
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Unable to delete", "Could not delete", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Unable to delete", data.msg, data.code);
			} else {
				notifySuccess(data.msg);
				if ($browse.entryDirPath === $browse.path) {
					reloadDir();
				} else {
					loadDir($browse.epname, $browse.entryDirPath);
				}
			}
	});
}

function doConnectServer() {
	$('#connect-m').modal('hide');
	$.post( '/xhr/connect', { _csrfp_token: $user.token, path: $('#connect-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Unable to connect to server", "Could not connect to server", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Unable to connect to server", data.msg, data.code);
			} else {
				
				loadDir('custom', '');
			}
	});
}

function setLayoutMode(newLayout) {
	if (newLayout == $user.layout) { return; }
	if (newLayout != 'grid' && newLayout != 'list') { return; }

	$.post( "/xhr/settings", { key: 'layout', value: newLayout, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Error switching layout", "Unable to save settings", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Error switching layout", data.msg, data.code);
			} else {
				if ($user.layout == "list") {
					$("#pdiv").removeClass("listview");
					$("#pdiv").addClass("gridview");
				} else {
					$("#pdiv").removeClass("gridview");
					$("#pdiv").addClass("listview");
				}

				if ($user.layout == "list") {
					$("#layout-button-icon").removeClass("fa-th-large");
					$("#layout-button-icon").addClass("fa-list");
				} else {
					$("#layout-button-icon").removeClass("fa-list");
					$("#layout-button-icon").addClass("fa-th-large");
				}

				$user.layout = newLayout;
				renderDirectory();
			}
		});
}

function setHidden(show_hidden) {
	if (show_hidden == $user.hidden) { return; }

	$.post( "/xhr/settings", { key: 'hidden', value: show_hidden, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Error setting hidden mode", "Unable to save settings", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Error setting hidden mode", data.msg, data.code);
			} else {
				if ($browse.btnsEnabled) {
					reloadDir();
				}
				$user.hidden = show_hidden;
			}
		});
}

function setClickMode(newMode) {
	if (newMode == $user.onclick) { return; }
	if (newMode != 'ask' && newMode != 'default' && newMode != 'download') { return; }

	$.post( "/xhr/settings", { key: 'click', value: newMode, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Error setting on click mode", "Unable to save settings", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Error setting upload mode", data.msg, data.code);
			} else {
				if ($browse.btnsEnabled) {
					reloadDir();
				}
				$user.onclick = newMode;
			}
		});
}

function setOverwrite(overwrite) {
	if (overwrite == $user.overwrite) { return; }
	$.post( "/xhr/settings", { key: 'overwrite', value: overwrite, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Error setting upload mode", "Unable to save settings", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Error setting upload mode", data.msg, data.code);
			} else {
				$user.overwrite = overwrite;
			}
		});
}

function setTheme(themeName) {
	if (themeName == $user.theme) { return; }
	$.post( "/xhr/settings", { key: 'theme', value: themeName, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			raiseFail("Error setting theme", "Unable to save settings", jqXHR, textStatus, errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code !== 0) {
				raiseNonZero("Error setting theme", data.msg, data.code);
			} else {
				$("body").fadeOut(200, function() {
					$("#theme-l").attr("href", "/static/themes/" + themeName + "/" + themeName + ".css");
					$("body").fadeIn(200);
				});

				if (data.navbar != $user.navbar) {
					if (data.navbar == 'default') {
						$(".navbar").removeClass("navbar-inverse");
						$(".navbar").addClass("navbar-default");
					} else if (data.navbar == 'inverse') {
						$(".navbar").removeClass("navbar-default");
						$(".navbar").addClass("navbar-inverse");
					}
				}

				$user.theme  = themeName;
				$user.navbar = data.navbar;
			}

		});
}

function onPageLoad() {
	/* load templating engine */
	var env = nunjucks.configure('/static/templates/',{ autoescape: true});
	env.addFilter('filesizeformat', filesizeformat);

	/* Enable shortcuts */
	Mousetrap.bind('alt+up', function() { 
		closeModals();
		browseParent(); 
	});

	Mousetrap.bind('alt+p', function() { 
		closeModals();
		$('#prefs-m').modal('show'); 
	});

	Mousetrap.bind('alt+s', function() {
		if ($browse.btnsEnabled === true) {
			closeModals();
			$('#search-m').modal('show'); 
		}
	});

	Mousetrap.bind('alt+n', function() {
		if ($browse.btnsEnabled === true) {
			closeModals();
			$('#mkdir-m').modal('show'); 
		}
	});

	Mousetrap.bind('alt+l', function() {
		switchLayout();
	});

	Mousetrap.bind('alt+u', function() {
		if ($browse.btnsEnabled === true) {
			closeModals();
			$('#upload-m').modal('show'); 
		}
	});

	Mousetrap.bind('alt+b', function() {
		if ($browse.btnsEnabled === true) {
			if ($browse.bmarkEnabled) {
				closeModals();
				$('#bmark-m').modal('show'); 
			}
		}
	});

	Mousetrap.bind('alt+c', function() {
		closeModals();
		$('#connect-m').modal('show'); 
	});


	/* Activate tooltips and enable hiding on clicking */
	$('[data-tooltip="yes"]').tooltip({"delay": { "show": 600, "hide": 100 }, "placement": "bottom", "trigger": "hover"});
	$('[data-tooltip="yes"]').on('mouseup', function () {$(this).tooltip('hide');});

	/* Load the preferences into the prefs modal */
	$('#prefs-m').on('show.bs.modal', function() {
		$('#prefs-layout-' + $user.layout).attr("checked", true);
		if ($user.hidden) {
			$('#prefs-hidden').attr("checked",true);
		}
		$('#prefs-click-' + $user.onclick).attr("checked",true);
		if ($user.overwrite) {
			$('#prefs-overwrite').attr("checked",true);
		}
		$('#prefs-theme-' + $user.theme).attr("checked",true);
	});

	/* Set up actions when preferences are changed */
	$('input[type=radio][name=prefs-layout-i]').change(function() {
		setLayoutMode(this.value);
	});

	$('#prefs-hidden').change(function() {
		setHidden(this.checked);
	});

	$('input[type=radio][name=prefs-click-i]').change(function() {
		setClickMode(this.value);
	});

	$('#prefs-overwrite').change(function() {
		setOverwrite(this.checked);
	});

	$('input[type=radio][name=prefs-theme-i]').change(function() {
		setTheme(this.value);
	});

	$("#layout-button").click(function () {
		switchLayout();
	});

	$("#e-rename-f").submit(function (e) {
		e.preventDefault();
		doRename();
	});

	$("#e-copy-f").submit(function (e) {
		e.preventDefault();
		doCopy();
	});

	$("#e-delete-f").submit(function (e) {
		e.preventDefault();
		doDelete();
	});

	$("#mkdir-f").submit(function (e) {
		e.preventDefault();
		doMkdir();
	});

	$("#search-f").submit(function (e) {
		e.preventDefault();
		doSearch();
	});

	$("#bmark-f").submit(function (e) {
		e.preventDefault();
		doBookmark();
	});

	$("#connect-f").submit(function (e) {
		e.preventDefault();
		doConnectServer();
	});

	/* handle back/forward buttons */
	window.addEventListener('popstate', function(e) {
		var previousState = e.state;
		if (previousState != null) {
			loadDir(previousState.epname, previousState.path, false);
		}
	});

	/* focus on inputs when modals open */
	$('#mkdir-m').on('shown.bs.modal', function() {
		$('#mkdir-m input[type="text"]').focus();
	});

	$('#connect-m').on('shown.bs.modal', function() {
		contents = $('#connect-m input[type="text"]').val();
		$('#connect-m input[type="text"]').focus().val("").val(contents);
	});
	
	$('#bmark-m').on('shown.bs.modal', function() {
		$('#bmark-m input[type="text"]').val($browse.data.bmark_path);
		$('#bmark-m input[type="text"]').focus();
	});

	$('#search-m').on('shown.bs.modal', function() {
		$('#search-m input[type="text"]').focus();
	});

	/* File uploads - drag files over shows a modal */
	$('body').dragster({
		enter: function ()
		{
			$('#upload-drag-m').modal();
		},
		leave: function ()
		{
			$('#upload-drag-m').modal('hide');
		}
	});

	/* Load initial directory */
	if (typeof $init !== 'undefined') {
		init_url = $init.epurl + '/browse/' + $init.path;
		history.replaceState({epurl: $init.epurl, epname: $init.epname, path: $init.path}, '', init_url);
		loadDir($init.epname, $init.path, false);
	}
}

$(document).ready(function($) {
	/* grab the user's settings from the server */
	$.getJSON('/xhr/settings')
	.done(function(response) {
		if (response.code !== 0) {
			raiseNonZero("Unable to load settings", response.msg, response.code);
		} else {
			$user.layout = response.layout;
			$user.token = response.token;
			$user.theme = response.theme;
			$user.navbar = response.navbar;
			$user.hidden = response.hidden;
			$user.overwrite = response.overwrite;
			$user.onclick = response.onclick;

			onPageLoad();
		}
	})
	.fail(function(jqXHR, textStatus, errorThrown) {
		raiseFail("Unable to load settings", "Unable to contact the server", jqXHR, textStatus, errorThrown);
	});
});

/* context (right click) menus */
(function ($, window) {
	$.fn.contextMenu = function (settings) {
		return this.each(function () {
			$(this).on("contextmenu", function (e) {
				if (e.ctrlKey) return;

				var $menu = $(settings.menuSelector).data("invokedOn", $(e.target)).show().css({
					position: "absolute",
					left: getMenuPosition(e.clientX, 'width', 'scrollLeft'),
					top: getMenuPosition(e.clientY, 'height', 'scrollTop')
				}).off('click').on('click', 'a', function (e) {
					$menu.hide();
					var $invokedOn = $menu.data("invokedOn");
					var $selectedMenu = $(e.target);
					settings.menuSelected.call(this, $invokedOn, $selectedMenu);
				});

				/* Extra code to show/hide view option based on type */
				$invokedOn = $menu.data("invokedOn");
				if ($invokedOn.closest(".efile").attr('data-view')) {
					$('#contextmenu_view').removeClass('hidden');
				}
				else {
					$('#contextmenu_view').addClass('hidden');
				}

				return false;
			});

			//make sure menu closes on any click
			$('body').click(function () {
				$(settings.menuSelector).hide();
			});
		});

		function getMenuPosition(mouse, direction, scrollDir) {
			var win = $(window)[direction](), scroll = $(window)[scrollDir](), menu = $(settings.menuSelector)[direction](), position = mouse + scroll;

			// opening menu would pass the side of the page
			if (mouse + menu > win && menu < mouse) {
				position -= menu;
			}

			return position;
		}
	};
})(jQuery, window);
