var currentUrl = null;
var currentEntry = null;
var currentEntryDirUrl = null;

function initDirectory(url)
{
	history.replaceState(url,"",url);
	loadDirectory(url,false);
}

function loadDirectory(url,alterHistory)
{
	if (alterHistory === undefined) { alterHistory = true; }

	$( "#browse" ).load( url + "?" + $.param({xhr: 1}), function( response, status, xhr )
	{
		if ( status == "error" ) {
			showError("Could not open directory","An error occured whilst contacting the server. ");
		}
		else {
			if (alterHistory) {
				history.pushState(url, "", url);
			}
			currentUrl = url;

			if (userLayout == "list") {
				doTable();
			}
			else {
				doGrid();
			}

			doBrowse();
			prepFileUpload();
		}
	});
}

function doSearch()
{
	$('#search-m').modal('hide');
	$( "#browse" ).load( currentUrl + "?" + $.param({'q': $('#search-i').val() }), function( response, status, xhr )
	{
		if ( status == "error" ) {
			showError("Could not search","An error occured whilst contacting the server. " + xhr.statusText);
		}
		else {
			doTable();

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
			//prepFileUpload();
		}
	});
}

function switchLayout()
{
	// work out the new layout
	if (userLayout == "list") {
		newLayout = "grid";
	}
	else {
		newLayout = "list";
	}

	// tell bargate to save the new layout
	$.post( "/settings/layout", { layout: newLayout, _csrfp_token: userToken })
		.fail(function(jqXHR, textStatus, errorThrown) {
			showError("Could not switch layout","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function() {
			// Now change classes/icons
			if (userLayout == "list") {
				$("#pdiv").removeClass("listview");
				$("#pdiv").addClass("gridview");
				$("#layout-button-icon").removeClass("fa-th-large");
				$("#layout-button-icon").addClass("fa-list");
			}
			else {
				$("#pdiv").removeClass("gridview");
				$("#pdiv").addClass("listview");
				$("#layout-button-icon").removeClass("fa-list");
				$("#layout-button-icon").addClass("fa-th-large");
			}
			userLayout = newLayout;
			loadDirectory(currentUrl);

	});
}

$( document ).ready(function() {
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

	/* handle back/forward buttons */
	window.addEventListener('popstate', function(e) {
		var requestedUrl = e.state;
		if (requestedUrl != null) {
			loadDirectory(requestedUrl,false);
		}
	});
});

function bytesToString(bytes,decimals)
{
	if (bytes == 0) return '0 Bytes';
	var sizes = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
	var i = Math.floor(Math.log(bytes) / Math.log(1024));
	return parseFloat((bytes / Math.pow(1024, i)).toFixed(1)) + ' ' + sizes[i];
}

function doTable()
{
	/* sort entries in a directory */
	$('.dir-sortby-name').on( 'click', function()
	{
		$('#dir').DataTable().order([3,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-name span').removeClass('invisible');
	});
	$('.dir-sortby-mtime').on( 'click', function()
	{
		$('#dir').DataTable().order([4,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-mtime span').removeClass('invisible');
	});
	$('.dir-sortby-type').on( 'click', function()
	{
		$('#dir').DataTable().order([5,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-type span').removeClass('invisible');
	});
	$('.dir-sortby-size').on( 'click', function()
	{
		$('#dir').DataTable().order([6,'asc']).draw();
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-size span').removeClass('invisible');
	});

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
		"order": [[3,"asc"]],
		"dom": 'lrtip'
	});
}

function doBrowse()
{
	$(".tdirclick").children("td").click(function() {
		loadDirectory( $(this).parent().data('url') );
	});

	$(".dirclick").click(function() {
		loadDirectory( $(this).data('url') );
	});

	// Bind actions to buttons in the 'file show' modal
	$("#e-rename-b").click(function () { showRename(); });
	$("#e-copy-b").click(function () { showCopy(); });
	$("#e-delete-b").click(function () { showDeleteFile(); });

	/* context (right click) menus */
	(function ($, window)
	{
		$.fn.contextMenu = function (settings)
		{
			return this.each(function ()
			{
				$(this).on("contextmenu", function (e)
				{
					if (e.ctrlKey) return;

					var $menu = $(settings.menuSelector).data("invokedOn", $(e.target)).show().css(
					{
						position: "absolute",
						left: getMenuPosition(e.clientX, 'width', 'scrollLeft'),
						top: getMenuPosition(e.clientY, 'height', 'scrollTop')
					}).off('click').on('click', 'a', function (e)
					{
						$menu.hide();
						var $invokedOn = $menu.data("invokedOn");
						var $selectedMenu = $(e.target);
						settings.menuSelected.call(this, $invokedOn, $selectedMenu);
					});

					/* Extra code to show/hide view option based on type */
					$invokedOn = $menu.data("invokedOn");
					if ($invokedOn.closest(".entry-click").attr('data-view'))
					{
						$('#contextmenu_view').removeClass('hidden');
					}
					else
					{
						$('#contextmenu_view').addClass('hidden');
					}

					return false;
				});

				//make sure menu closes on any click
				$('body').click(function ()
				{
					$(settings.menuSelector).hide();
				});
			});

			function getMenuPosition(mouse, direction, scrollDir)
			{
				var win = $(window)[direction](), scroll = $(window)[scrollDir](), menu = $(settings.menuSelector)[direction](), position = mouse + scroll;

				// opening menu would pass the side of the page
				if (mouse + menu > win && menu < mouse) 
				{
					position -= menu;
				}

				return position;
			}
		};
	})(jQuery, window);

	/**************************************************************************/
	
	$(".entry-preview").click(function() {
		var parent = $(this).closest('.entry-click');
		
		$('#file-click-filename').text(parent.data('filename'));
		$('#file-click-size').text(parent.data('size'));
		$('#file-click-mtime').text(parent.data('mtime'));
		$('#file-click-mtype').text(parent.data('mtype'));
		$('#file-click-icon').attr('class',parent.data('icon'));
		$('#file-click-download').attr('href',parent.data('download'));
		$('#file-click-details').data('stat',parent.data('stat'));
		
		if (parent.attr('data-imgpreview')) {
			$('#file-click-preview').attr('src',parent.data('imgpreview'));
			$('#file-click-preview').removeClass('hidden');
			$('#file-click-icon').addClass('hidden');
		}
		else {
			$('#file-click-preview').attr('src','');
			$('#file-click-preview').addClass('hidden');
			$('#file-click-icon').removeClass('hidden');
		}
		
		if (parent.attr('data-view')) {
			$('#file-click-view').attr('href',parent.data('view'));
			$('#file-click-view').removeClass('hidden');
		}
		else {
			$('#file-click-view').addClass('hidden');
		}

		if (parent.attr('data-parent')) {
			selectEntry(parent.data('filename'),parent.data('parent'));
		} else {
			selectEntry(parent.data('filename'),currentUrl);
		}

		$('#file-click').modal('show');
	});

	$("#file-click-details").click(function()
	{
		$('#file-details-loading').removeClass('hidden');
		$('#file-details-data').addClass('hidden');
		$('#file-details-error').addClass('hidden');
		$('#file-details-filename').html('Please wait...');
		$('#file-details').modal({show: true});

		$.getJSON($(this).data('stat'), function(data)
		{
			if (data.error == 1) {
				$('#file-details-reason').html(data.reason);
				$('#file-details-filename').html('Uh oh');
				$('#file-details-loading').addClass('hidden');
				$('#file-details-error').removeClass('hidden');
			}
			else
			{
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
	});

	/* right click menu for files */
	$(".entry-file").contextMenu(
	{
		menuSelector: "#fileContextMenu",
		menuSelected: function (invokedOn, selectedMenu)
		{
			var parentRow = invokedOn.closest(".entry-click");
			var $action = selectedMenu.closest("a").data("action");

			if ($action == 'view') {
				window.open(parentRow.data('view'),'_blank');
			}
			else if ($action == 'download') {
				window.open(parentRow.data('download'),'_blank');
			}
			else if ($action == 'copy') {
				selectEntry(parentRow.data('filename'),currentUrl);
				showCopy();
			}
			else if ($action == 'rename') {
				selectEntry(parentRow.data('filename'),currentUrl);
				showRename();
			}
			else if ($action == 'delete') {
				selectEntry(parentRow.data('filename'),currentUrl);
				showDeleteFile();
			}
			else if ($action == 'properties') {
				$('#file-details-loading').removeClass('hidden');
				$('#file-details-data').addClass('hidden');
				$('#file-details-filename').html('Please wait...');
				$('#file-details').modal({show: true});

				$.getJSON(parentRow.data('stat'), function(data)
				{
					$('#file-details-filename').html(data.filename);
					$('#file-details-size').html(bytesToString(data.size));
					$('#file-details-atime').html(data.atime);
					$('#file-details-mtime').html(data.mtime);
					$('#file-details-ftype').html(data.ftype);
					$('#file-details-owner').html(data.owner);
					$('#file-details-group').html(data.group);

					$('#file-details-loading').addClass('hidden');
					$('#file-details-data').removeClass('hidden');
				});
			}

			event.preventDefault();
			event.stopPropagation();
		}
	});

	/* context menu for directories */
	$(".entry-dir").contextMenu(
	{
		menuSelector: "#dirContextMenu",
		menuSelected: function (invokedOn, selectedMenu) {
			var parentRow = invokedOn.closest(".entry-click");
			var $action = selectedMenu.closest("a").data("action");

			if ($action == 'open') {
				loadDirectory(parentRow.data('url'));
			}
			else if ($action == 'rename') {
				showRename(parentRow.data('filename'));
			}
			else if ($action == 'delete') {
				showDeleteDirectory(parentRow.data('filename'));
			}

			event.preventDefault();
			event.stopPropagation();
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

	/* Searching - mark as 'searching' for long page loads */
	$("#search-form" ).submit(function( event ) {
		$("#search-form-submit").button('loading');
	});
}

function doGrid() {
	var $container = $('#files').isotope({
		getSortData:
		{
			name: '[data-sortname]',
			type: '[data-raw-mtype]',
			mtime: '[data-raw-mtime] parseInt',
			size: '[data-raw-size] parseInt',
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
		sortBy: 'name',
	});

	/* sort entries in a directory */
	$('.dir-sortby-name').on( 'click', function() {
		$container.isotope({ sortBy: 'name' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-name span').removeClass('invisible');
	});
	$('.dir-sortby-mtime').on( 'click', function() {
		$container.isotope({ sortBy: 'mtime' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-mtime span').removeClass('invisible');
	});
	$('.dir-sortby-type').on( 'click', function() {
		$container.isotope({ sortBy: 'type' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-type span').removeClass('invisible');
	});
	$('.dir-sortby-size').on( 'click', function() {
		$container.isotope({ sortBy: 'size' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-size span').removeClass('invisible');
	});

	var $dirs = $('#dirs').isotope( {
		getSortData: { name: '[data-sortname]',},
		sortBy: 'name',
	});

}

function formatFileSize(bytes) {
	if (typeof bytes !== 'number') {
		return '';
	}
	if (bytes >= 1000000000) {
		return (bytes / 1000000000).toFixed(2) + ' GB';
	}
	if (bytes >= 1000000) {
		return (bytes / 1000000).toFixed(2) + ' MB';
	}
	return (bytes / 1000).toFixed(2) + ' KB';
}

function formatBitrate(bits) {
	if (typeof bits !== 'number') {
		return '';
	}

	bits = bits / 8

	if (bits >= 1000000000) {
		return (bits / 1000000000).toFixed(2) + ' GiB/s';
	}
	if (bits >= 1000000) {
		return (bits / 1000000).toFixed(2) + ' MiB/s';
	}
	if (bits >= 1000) {
		return (bits / 1000).toFixed(2) + ' KiB/s';
	}
	return bits.toFixed(2) + ' bytes/s';
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
	return formatBitrate(data.bitrate) + ', ' + formatTime((data.total - data.loaded) * 8 / data.bitrate) + ' remaining <br/>' + formatFileSize(data.loaded) + ' uploaded of ' + formatFileSize(data.total);
}

function prepFileUpload() {
	$('#fileupload').fileupload({
		url: currentUrl,
		dataType: 'json',
		maxChunkSize: 10485760, // 10MB
		formData: [{name: '_csrfp_token', value: userToken}, {name: 'action', value: 'jsonupload'}],
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
					loadDirectory(currentUrl);
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
	currentEntry = name;
	currentEntryDirUrl = url;
}

function showRename() {
	$('#e-rename-i').val(currentEntry);
	$('#e-rename-m').modal('show');
	$('#e-rename-i').focus();
}

function showCopy() {
	$('#e-copy-i').val("Copy of " + currentEntry);
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
	$('#e-delete-n').text(currentEntry);
	$('#e-delete-m').modal('show');
}

function showMkdir() {
	$('#e-mkdir-m').modal('show');
	$('#e-mkdir-i').focus();
}

function notifySuccess(msg)
{
	$.notify({ icon: 'fa fa-fw fa-check', message: msg },{ type: 'success', placement: {align: 'center', from: 'bottom'}});
}

function doRename()
{
	$('#e-rename-m').modal('hide');

	$.post( currentEntryDirUrl, { action: 'rename', _csrfp_token: userToken, old_name: currentEntry, new_name: $('#e-rename-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showError("Could not rename","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showError("Could not rename",data.msg);
			}
			else {
				notifySuccess(data.msg);
				loadDirectory(currentEntryDirUrl);
			}
	});
}

function doCopy()
{
	$('#e-copy-m').modal('hide');

	$.post( currentEntryDirUrl, { action: 'copy', _csrfp_token: userToken, src: currentEntry, dest: $('#e-copy-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showError("Could not copy","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showError("Could not copy",data.msg);
			}
			else {
				notifySuccess(data.msg);
				loadDirectory(currentEntryDirUrl);
			}
	});
}

function doMkdir()
{
	$('#mkdir-m').modal('hide');

	$.post( currentEntryDirUrl, { action: 'mkdir', _csrfp_token: userToken, name: $('#mkdir-i').val()})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showError("Could not create directory","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showError("Could not create directory",data.msg);
			}
			else {
				notifySuccess(data.msg);
				loadDirectory(currentEntryDirUrl);
			}
	});
}

function doDelete()
{
	$('#e-delete-m').modal('hide');

	$.post( currentEntryDirUrl, { action: 'delete', _csrfp_token: userToken, name: currentEntry})
		.fail(function(jqXHR, textStatus, errorThrown) {
			showError("Could not delete","An error occured whilst contacting the server. " + errorThrown);
		})
		.done(function(data, textStatus, jqXHR) {
			if (data.code != 0) {
				showError("Could not delete",data.msg);
			}
			else {
				notifySuccess(data.msg);
				loadDirectory(currentEntryDirUrl);
			}
	});
}
