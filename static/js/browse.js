/* browse mode (directory listings) javascript */
$(document).ready(function()
{
	/* context menus */
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
					if ($invokedOn.closest(".entry").attr('data-view'))
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


	$(".entry-open").click(function()
	{
		window.document.location = $(this).data('url');
	});
	
	$(".entry-preview").click(function()
	{
		var parent = $(this)
		
		$('#file-click-filename').text(parent.data('filename'));
		$('#file-click-size').text(parent.data('size'));
		$('#file-click-mtime').text(parent.data('mtime'));
		$('#file-click-mtype').text(parent.data('mtype'));
		$('#file-click-icon').attr('class',parent.data('icon'));
		$('#file-click-download').attr('href',parent.data('download'));
		$('#file-click-props').attr('href',parent.data('props'));
		
		if (parent.attr('data-imgpreview'))
		{
			$('#file-click-preview').attr('src',parent.data('imgpreview'));
			$('#file-click-preview').removeClass('hidden');
			$('#file-click-icon').addClass('hidden');
		}
		else
		{
			$('#file-click-preview').attr('src','');
			$('#file-click-view').addClass('hidden');
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
		
		$('#file-click').modal();
	});
	  
	var $container = $('#files').isotope(
	{
		getSortData:
		{
			name: '[data-filename]',
			type: '[data-raw-mtype]',
			mtime: '[data-raw-mtime] parseInt',
			size: '[data-raw-size] parseInt',
		},
		transitionDuration: '0',
		sortAscending:
		{
			name: true,
			type: true,
			mtime: false,
			size: false
		}
	});


	$('.dir-sortby-name').on( 'click', function()
	{
		$container.isotope({ sortBy: 'name' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-name span').removeClass('invisible');
	});
	$('.dir-sortby-type').on( 'click', function()
	{
		$container.isotope({ sortBy: 'type' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-type span').removeClass('invisible');
	});
	$('.dir-sortby-mtime').on( 'click', function()
	{
		$container.isotope({ sortBy: 'mtime' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-mtime span').removeClass('invisible');
	});
	$('.dir-sortby-size').on( 'click', function()
	{
		$container.isotope({ sortBy: 'size' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-size span').removeClass('invisible');
	});


	$(".entry-file").contextMenu(
	{
		menuSelector: "#fileContextMenu",
		menuSelected: function (invokedOn, selectedMenu)
		{
			var parentRow = invokedOn.closest(".entry");

			if (selectedMenu.data('action') == 'view')
			{
				window.document.location = parentRow.data('view');
			}
			else if (selectedMenu.data('action') == 'download')
			{
				window.document.location = parentRow.data('download');
			}
			else if (selectedMenu.data('action') == 'copy')
			{
				$('#copy_path').val(parentRow.data('path'));
				$('#copyfilename').attr('value',"Copy of " + parentRow.data('filename'));
				$('#copy-file').modal({show: true});
				$('#copyfilename').focus();
			}
			else if (selectedMenu.data('action') == 'rename')
			{
				$('#rename_path').val(parentRow.data('path'));
				$('#newfilename').attr('value',parentRow.data('filename'));
				$('#rename-file').modal({show: true});
				$('#newfilename').focus();
			}
			else if (selectedMenu.data('action') == 'delete')
			{
				$('#delete_path').val(parentRow.data('path'));
				$('#delete_filename').html(parentRow.data('filename'));		
				$('#delete-confirm').modal({show: true});
			}
			else if (selectedMenu.data('action') == 'properties')
			{
				window.document.location = parentRow.data('props');			
			}

			event.preventDefault();
			event.stopPropagation();
		}
	});

	$(".entry-directory").contextMenu(
	{
		menuSelector: "#dirContextMenu",
		menuSelected: function (invokedOn, selectedMenu)
		{
			var parentRow = invokedOn.closest(".entry");

			if (selectedMenu.data('action') == 'open')
			{
				window.document.location = parentRow.data('url');
			}
			else if (selectedMenu.data('action') == 'rename')
			{
				$('#rename_path').val(parentRow.data('path'));
				$('#newfilename').attr('value',parentRow.data('filename'));
				$('#rename-file').modal({show: true});
				$('#newfilename').focus();
			}
			else if (selectedMenu.data('action') == 'delete')
			{
				$('#delete_dir_path').val(parentRow.data('path'));
				$('#delete-dir-confirm').modal({backdrop: 'static', show: true});
			}

			event.preventDefault();
			event.stopPropagation();
		}
	});

});
