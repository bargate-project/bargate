function bytesToString(bytes,decimals)
{
	if (bytes == 0) return '0 Bytes';
	var sizes = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
	var i = Math.floor(Math.log(bytes) / Math.log(1024));
	return parseFloat((bytes / Math.pow(1024, i)).toFixed(1)) + ' ' + sizes[i];
}

/* browse mode (directory listings) javascript */
$(document).ready(function()
{
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
	
	$(".entry-preview").click(function()
	{
		var parent = $(this).closest('.entry-click');
		
		$('#file-click-filename').text(parent.data('filename'));
		$('#file-click-size').text(parent.data('size'));
		$('#file-click-mtime').text(parent.data('mtime'));
		$('#file-click-mtype').text(parent.data('mtype'));
		$('#file-click-icon').attr('class',parent.data('icon'));
		$('#file-click-download').attr('href',parent.data('download'));
		$('#file-click-details').data('stat',parent.data('stat'));
		
		if (parent.attr('data-imgpreview'))
		{
			$('#file-click-preview').attr('src',parent.data('imgpreview'));
			$('#file-click-preview').removeClass('hidden');
			$('#file-click-icon').addClass('hidden');
		}
		else
		{
			$('#file-click-preview').attr('src','');
			$('#file-click-preview').addClass('hidden');
			$('#file-click-icon').removeClass('hidden');
		}
		
		if (parent.attr('data-view'))
		{
			$('#file-click-view').attr('href',parent.data('view'));
			$('#file-click-view').removeClass('hidden');
		}
		else
		{
			$('#file-click-view').addClass('hidden');
		}

		/* We also prime the 'rename', 'delete' and 'copy' modals as if they have
			been clicked because they can be clicked from this modal */

		$('#copy_path').val(parent.data('path'));
		$('#copyfilename').attr('value',"Copy of " + parent.data('filename'));		
		$('#rename_path').val(parent.data('path'));
		$('#newfilename').attr('value',parent.data('filename'));
		$('#delete_path').val(parent.data('path'));
		$('#delete_filename').html(parent.data('filename'));	
		
		$('#file-click').modal();
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

			if ($action == 'view')
			{
				window.document.location = parentRow.data('view');
			}
			else if ($action == 'download')
			{
				window.document.location = parentRow.data('download');
			}
			else if ($action == 'copy')
			{
				$('#copy_path').val(parentRow.data('path'));
				$('#copyfilename').attr('value',"Copy of " + parentRow.data('filename'));
				$('#copy-file').modal({show: true});
				$('#copyfilename').focus();
			}
			else if ($action == 'rename')
			{
				$('#rename_path').val(parentRow.data('path'));
				$('#newfilename').attr('value',parentRow.data('filename'));
				$('#rename-file').modal({show: true});
				$('#newfilename').focus();
			}
			else if ($action == 'delete')
			{
				$('#delete_path').val(parentRow.data('path'));
				$('#delete_filename').html(parentRow.data('filename'));		
				$('#delete-confirm').modal({show: true});
			}
			else if ($action == 'properties')
			{
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

				/*window.document.location = parentRow.data('props');*/
			}
			else
			{
				console.log("WARNING: contextMenu item click UNMATCHED. data value was: " + selectedMenu.data('action'));
			}

			event.preventDefault();
			event.stopPropagation();
		}
	});

	/* right click menu for directories */
	$(".entry-dir").contextMenu(
	{
		menuSelector: "#dirContextMenu",
		menuSelected: function (invokedOn, selectedMenu)
		{
			var parentRow = invokedOn.closest(".entry-click");
			var $action = selectedMenu.closest("a").data("action");

			if ($action == 'open')
			{
				window.document.location = parentRow.data('url');
			}
			else if ($action == 'rename')
			{
				$('#rename_path').val(parentRow.data('path'));
				$('#newfilename').attr('value',parentRow.data('filename'));
				$('#rename-file').modal({show: true});
				$('#newfilename').focus();
			}
			else if ($action == 'delete')
			{
				$('#delete_dir_path').val(parentRow.data('path'));
				$('#delete-dir-confirm').modal({backdrop: 'static', show: true});
			}

			event.preventDefault();
			event.stopPropagation();
		}
	});

	/* focus on inputs when modals open */
	$('#create-directory').on('shown.bs.modal', function() {
		$('#create-directory input[type="text"]').focus();
	});
	
	$('#add-bookmark').on('shown.bs.modal', function() {
		$('#add-bookmark input[type="text"]').focus();
	});

	$('#search').on('shown.bs.modal', function() {
		$('#search input[type="text"]').focus();
	});

	/* meh...don't set focus back on buttons when modals are closed */
	$('#create-directory').on('shown.bs.modal', function(e)
	{
		$('#create-directory-button').one('focus', function(e){$(this).blur();});
	});

	$('#upload-file').on('shown.bs.modal', function(e)
	{
		$('#upload-button').one('focus', function(e){$(this).blur();});
	});


	/* File uploads - drag files over shows a modal */
	$('body').dragster(
	{
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
	$("#search-form" ).submit(function( event )
	{
		$("#search-form-submit").button('loading');
	});
});
