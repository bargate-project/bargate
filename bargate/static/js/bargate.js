function showErr(title,desc) {
	$('.modal').modal('hide');
	$("#modal-error-title").text(title);
	$("#modal-error-desc").text(desc);
	$('#modal-error').modal('show');
}

var $browse = {url: null, entry: null, entryDirUrl: null, btnsEnabled: false,
	bmarkEnabled: false, sortBy: 'name'
};

function enableBrowseButts() {
	if (!$browse.btnsEnabled === true) {
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

function initDirectory(url) {
	history.replaceState(url,"",url);
	loadDir(url,false);
}

function loadDir(url,alterHistory) {
	if (alterHistory === undefined) { alterHistory = true; }

	$.getJSON(url, {xhr: 1})
	.done(function(response) {
		if (response.code > 0) {
			showErr("Could not open folder",response.msg);
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

			$('#browse').html(nunjucks.render('breadcrumbs.html', { crumbs: response.crumbs, root_name: response.root_name, root_url: response.root_url }));

			if (response.no_items) {
				$('#browse').append(nunjucks.render('empty.html'));
			} else {
				$('#browse').append(nunjucks.render('directory-' + $user.layout + '.html', {dirs: response.dirs, files: response.files, shares: response.shares, baseurl: baseurl}));
			}

			if (alterHistory) {
				history.pushState(url, "", url);
			}
			$browse.url = url;

			if ($user.layout == "list") {
				doListView();
			}
			else {
				doGridView();
			}

			doBrowse();
			prepFileUpload();
		}
	})
	.fail(function() {
		showErr("Server error","The server returned an error");
	});
}

function doSearch() {
	$('#search-m').modal('hide');

	$.getJSON($browse.url, {q: $('#search-i').val()})
	.done(function(response) {
		if (response.code > 0) {
			showErr("Search failed",response.msg);
		} else {
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
	.fail(function() {
		showErr("Server error","The server returned an error");
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
		loadDir( $(this).data('url') );
		event.preventDefault();
		event.stopPropagation();
	});

	$(".eshare").click(function() {
		loadDir( $(this).data('url') );
	});

	// Bind actions to buttons in the 'file show' modal
	$("#e-rename-b").click(function () { showRename(); });
	$("#e-copy-b").click(function () { showCopy(); });
	$("#e-delete-b").click(function () { showDeleteFile(); });

	/* What to do when a user clicks a file entry in a listing */
	$(".efile").click(function() {
		if ($user.onclick == 'ask') {
			showFileOverview($(this));
		} else if ($user.onclick == 'default') {
			if ($(this).attr('data-view')) {
				window.open(baseurl($(this).data('burl'),$(this).data('path'),'view'),'_blank');
			} else {
				window.open(baseurl($(this).data('burl'),$(this).data('path'),'download'),'_blank');
			}
		} else {
			window.open(baseurl($(this).data('burl'),$(this).data('path'),'download'),'_blank');
		}
	});

	$("#file-click-details").click(function() {
		showFileDetails($(this));
	});

	/* right click menu for files */
	$(".efile").contextMenu({
		menuSelector: "#fileContextMenu",
		menuSelected: function (invokedOn, selectedMenu)
		{
			var file = invokedOn.closest(".efile");
			var $action = selectedMenu.closest("a").data("action");

			if ($action == 'view') {
				window.open(baseurl(file.data('burl'),file.data('path'),'view'),'_blank');
			}
			else if ($action == 'download') {
				window.open(baseurl(file.data('burl'),file.data('path'),'download'),'_blank');
			}
			else if ($action == 'copy') {
				selectEntry(file.data('filename'),$browse.url);
				showCopy();
			}
			else if ($action == 'rename') {
				selectEntry(file.data('filename'),$browse.url);
				showRename();
			}
			else if ($action == 'delete') {
				selectEntry(file.data('filename'),$browse.url);
				showDeleteFile();
			}
			else if ($action == 'properties') {
				showFileDetails(file);
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
				loadDir(dir.data('url'));
			}
			else if ($action == 'rename') {
				showRename(dir.data('filename'));
			}
			else if ($action == 'delete') {
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
	var bytes = parseFloat(bytes);
	var units = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

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
			return match;
		});
	}
}

function bitrateformat(bits) {
	var bytes = bytes / 8
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

function formatTime (seconds) {
	var date = new Date(seconds * 1000),
		days = Math.floor(seconds / 86400);
	days = days ? days + 'd ' : '';
	return days +
		('0' + date.getUTCHours()).slice(-2) + ':' +
		('0' + date.getUTCMinutes()).slice(-2) + ':' +
		('0' + date.getUTCSeconds()).slice(-2);
}

function renderExtendedProgress(data) {
	return bitrateformat(data.bitrate) + ', ' + formatTime((data.total - data.loaded) * 8 / data.bitrate) + ' remaining <br/>' + filesizeformat(data.loaded) + ' uploaded of ' + formatFileSize(data.total);
}

function prepFileUpload() {
	$('#fileupload').fileupload({
		url: $browse.url,
		dataType: 'json',
		maxChunkSize: 10485760, // 10MB
		formData: [{name: '_csrfp_token', value: $user.token}, {name: 'action', value: 'upload'}],
		start: function (e) {
			$('#upload-drag-over').modal('hide');
			$('#upload-file').modal()
			$('#upload-progress').removeClass('hidden');
			$('#upload-progress-ext').removeClass('hidden');
			$('#upload-cancel').removeClass('hidden');
			
			$('#upload-button-icon').removeClass('fa-upload');
			$('#upload-button-icon').addClass('fa-spin');
			$('#upload-button-icon').addClass('fa-cog');
		},
		stop: function (e, data) {
			$('#upload-button-icon').addClass('fa-upload');
			$('#upload-button-icon').removeClass('fa-spin');
			$('#upload-button-icon').removeClass('fa-cog');

			$('#upload-progress').addClass('hidden');
			$('#upload-progress-ext').addClass('hidden');
			$('#upload-cancel').addClass('hidden');

			if (!($("#upload-file").data('bs.modal').isShown)) {
				/* if something finished then show the modal if it wasnt already */
				$('#upload-file').modal('show');
			}
		},
		done: function (e, data) {
			window.uploadsuccess = 1;
			$.each(data.result.files, function (index, file) {
				if (file.error) {
					$('<li><span class="label label-danger"><i class="fa fa-fw fa-exclamation"></i></span> &nbsp; Could not upload ' + file.name + ': ' + file.error + ' </li>').prependTo('#upload-files');
				}
				else {
					$('<li><span class="label label-success"><i class="fa fa-fw fa-check"></i></span> &nbsp; Uploaded ' + file.name + '</li>').prependTo('#upload-files');
					loadDir($browse.url);
				}
			});
		},
		fail: function (e, data) {
			window.uploadsuccess = 0;

			if (data.errorThrown === 'abort') {
				$('<li><span class="label label-warning"><i class="fa fa-fw fa-check"></i></span> &nbsp; Upload cancelled </li>').prependTo('#upload-files');
			}
			else {
				$('<li><span class="label label-danger"><i class="fa fa-fw fa-exclamation"></i></span> &nbsp; Could not upload file(s). The server said: ' + data.errorThrown + ' </li>').prependTo('#upload-files');
			}
		},
		progressall: function (e, data) {
			var progress = parseInt(data.loaded / data.total * 100, 10);
			$('#upload-progress-pc').html(progress);
			$('#upload-progress .progress-bar').css('width', progress + '%');
			$('#upload-progress-ext').html(renderExtendedProgress(data));
		},
		add: function (e, data) {
			jqXHR = data.submit();
			$('#upload-cancel').click(function (e) {
				jqXHR.abort();
			});
		},
	}).prop('disabled', !$.support.fileInput).parent().addClass($.support.fileInput ? undefined : 'disabled');
}

function selectEntry(name,url) {
	$browse.entry = name;
	$browse.entryDirUrl = url;
}

function baseurl(burl,path,action) {
	return burl + "/" + action + "/" + path
}

function showFileDetails(file) {
	$('#file-details-loading').removeClass('hidden');
	$('#file-details-data').addClass('hidden');
	$('#file-details-filename').html('Please wait...');
	$('#file-details').modal('show');

	$.getJSON(baseurl(file.data('burl'),file.data('path'),'stat'), function(data) {
		if (data.error == 1) {
			showErr("Could not load file details",data.reason);
		} else {
			$('#file-details-filename').html(data.filename);
			$('#file-details-size').html(bytesToString(data.size));
			$('#file-details-atime').html(data.atime);
			$('#file-details-mtime').html(data.mtime);
			$('#file-details-ftype').html(data.ftype);
			$('#file-details-owner').html(data.owner);
			$('#file-details-group').html(data.group);

			$('#file-details-loading').addClass('hidden');
			$('#file-details-data').removeClass('hidden');
		}
	});
}

function showFileOverview(file) {
	$('#file-click-filename').text(file.data('filename'));
	$('#file-click-size').text(file.data('size'));
	$('#file-click-mtime').text(file.data('mtime'));
	$('#file-click-mtype').text(file.data('mtype'));
	$('#file-click-icon').attr('class',file.data('icon'));
	$('#file-click-download').attr('href',baseurl(file.data('burl'),file.data('path'),'download'));
	$('#file-click-details').data('burl',file.data('burl'));
	$('#file-click-details').data('path',file.data('path'));

	
	if (file.attr('data-img')) {
		$('#file-click-preview').attr('src',baseurl(file.data('burl'),file.data('path'),'preview'));
		$('#file-click-preview').removeClass('hidden');
		$('#file-click-icon').addClass('hidden');
	}
	else {
		$('#file-click-preview').attr('src','');
		$('#file-click-preview').addClass('hidden');
		$('#file-click-icon').removeClass('hidden');
	}
	
	if (file.attr('data-view')) {
		$('#file-click-view').attr('href',baseurl(file.data('burl'),file.data('path'),'view'));
		$('#file-click-view').removeClass('hidden');
	}
	else {
		$('#file-click-view').addClass('hidden');
	}

	if (file.attr('data-parent')) {
		selectEntry(file.data('filename'),file.data('parent'));
	} else {
		selectEntry(file.data('filename'),$browse.url);
	}

	$('#file-click').modal('show');
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
	$.notify({ icon: 'fa fa-fw fa-check', message: msg },{ type: 'success', placement: {align: 'center', from: 'bottom'}});
}

function doRename() {
	$('#e-rename-m').modal('hide');
	$.post( $browse.entryDirUrl, { action: 'rename', _csrfp_token: $user.token, old_name: $browse.entry, new_name: $('#e-rename-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not rename","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showErr("Could not rename",data.msg);
			} else {
				notifySuccess(data.msg);
				loadDir($browse.entryDirUrl);
			}
	});
}

function doCopy() {
	$('#e-copy-m').modal('hide');
	$.post( $browse.entryDirUrl, { action: 'copy', _csrfp_token: $user.token, src: $browse.entry, dest: $('#e-copy-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not copy","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showErr("Could not copy",data.msg);
			} else {
				notifySuccess(data.msg);
				loadDir($browse.entryDirUrl);
			}
	});
}

function doMkdir() {
	$('#mkdir-m').modal('hide');
	$.post( $browse.url, { action: 'mkdir', _csrfp_token: $user.token, name: $('#mkdir-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not create directory","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showErr("Could not create directory",data.msg);
			} else {
				notifySuccess(data.msg);
				loadDir($browse.url);
			}
	});
}

function doBookmark() {
	$('#bmark-m').modal('hide');
	bmarkName = $('#bmark-i').val();
	$.post( $browse.url, { action: 'bookmark', _csrfp_token: $user.token, name: bmarkName})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not create bookmark","An error occured whilst contacting the server.");
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showErr("Could not create bookmark",data.msg);
			} else {
				notifySuccess(data.msg);
				$('#bmarks').append('<li><a href="' + data.url + '"><i class="fa fa-arrow-right fa-fw"></i>' + bmarkName + '</a></li>');
			}
	});
}

function doDelete() {
	$('#e-delete-m').modal('hide');
	$.post( $browse.entryDirUrl, { action: 'delete', _csrfp_token: $user.token, name: $browse.entry})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not delete","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showErr("Could not delete",data.msg);
			} else {
				notifySuccess(data.msg);
				loadDir($browse.entryDirUrl);
			}
	});
}

function setLayoutMode(newLayout) {
	if (newLayout == $user.layout) { return; }
	if (newLayout != 'grid' && newLayout != 'list') { return; }

	$.post( "/settings", { key: 'layout', value: newLayout, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not switch layout","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function() {
			if ($browse.btnsEnabled) {

				// Now change view class
				if ($user.layout == "list") {
					$("#pdiv").removeClass("listview");
					$("#pdiv").addClass("gridview");
				} else {
					$("#pdiv").removeClass("gridview");
					$("#pdiv").addClass("listview");
				}

				loadDir($browse.url);
			}

			if ($user.layout == "list") {
				$("#layout-button-icon").removeClass("fa-th-large");
				$("#layout-button-icon").addClass("fa-list");
			} else {
				$("#layout-button-icon").removeClass("fa-list");
				$("#layout-button-icon").addClass("fa-th-large");
			}

			$user.layout = newLayout;
		});
}

function setHidden(show_hidden) {
	if (show_hidden == $user.hidden) { return; }

	$.post( "/settings", { key: 'hidden', value: show_hidden, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not set hidden files mode","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function() {
			if ($browse.btnsEnabled) {
				loadDir($browse.url);
			}
			$user.hidden = show_hidden;
		});
}

function setClickMode(newMode) {
	if (newMode == $user.onclick) { return; }
	if (newMode != 'ask' && newMode != 'default' && newMode != 'download') { return; }

	$.post( "/settings", { key: 'click', value: newMode, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not set on click mode","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function() {
			if ($browse.btnsEnabled) {
				loadDir($browse.url);
			}
			$user.onclick = newMode;
		});
}

function setOverwrite(overwrite) {
	if (overwrite == $user.overwrite) { return; }
	$.post( "/settings", { key: 'overwrite', value: overwrite, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not set upload overwrite mode","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function() {
			$user.overwrite = overwrite;
		});
}

function setTheme(themeName) {
	if (themeName == $user.theme) { return; }
	$.post( "/settings", { key: 'theme', value: themeName, _csrfp_token: $user.token })
		.fail(function(jqXHR, textStatus, errorThrown) {
			showErr("Could not change theme","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
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

		});
}

$(document).ready(function($) {
	/* load templating engine */
	var env = nunjucks.configure('/static/templates/', { autoescape: true });
	env.addFilter('filesizeformat', filesizeformat);
	
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

	/* handle back/forward buttons */
	window.addEventListener('popstate', function(e) {
		var requestedUrl = e.state;
		if (requestedUrl != null) {
			loadDir(requestedUrl,false);
		}
	});

	/* focus on inputs when modals open */
	/* these modals are triggered by data-toggle, so we must do it here */
	$('#mkdir-m').on('shown.bs.modal', function() {
		$('#mkdir-m input[type="text"]').focus();
	});
	
	$('#bmark-m').on('shown.bs.modal', function() {
		$('#bmark-m input[type="text"]').focus();
	});

	$('#search-m').on('shown.bs.modal', function() {
		$('#search-m input[type="text"]').focus();
	});

	/* File uploads - drag files over shows a modal */
	$('body').dragster({
		enter: function ()
		{
			$('#upload-drag-over').modal()
		},
		leave: function ()
		{
			$('#upload-drag-over').modal('hide');
		}
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
