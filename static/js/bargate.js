/* BARGATE LOCAL JAVASCRIPT */

/* Popup error modal show, if any */
$(window).load(function(){
	$('#popup-error').modal('show');
});

/* Tablesorter enable */
$(document).ready(function() 
    { 
        $("#dir").tablesorter();
    } 
);

/* Tooltip */
$(document).ready(function ()
{
	$("[rel=tooltip]").tooltip();
});

jQuery(document).ready(function($)
{
	$(".rowclick-td").click(function()
	{
		window.document.location = $(this).parent().data('url');
	});
	
	$(".mclick-td").click(function()
	{
		$('#file-click-filename').text($(this).parent().data('filename'));
		$('#file-click-size').text($(this).parent().data('size'));
		$('#file-click-mtime').text($(this).parent().data('mtime'));
		$('#file-click-mtype').text($(this).parent().data('mtype'));
		$('#file-click-icon').attr('class','fa fa-2x' + $(this).parent().data('icon'));
		$('#file-click-url').attr('href',$(this).parent().data('url'));
		$('#file-click-props').attr('href',$(this).parent().data('props'));
		$('#file-click').modal();
	});
	
	$('.fcog').on('shown.bs.dropdown', function ()
	{
		var menu = $(this).find('.dropdown-menu');

		if (menu.visible() )
		{
			/*console.log('menu is visible');*/
			/*$(this).parent().removeClass('dropup');*/
		}
		else
		{
			$(this).parent().addClass('dropup');
			
		}
	});
	
	$('.fcog').on('hidden.bs.dropdown', function ()
	{
		$(this).parent().removeClass('dropup');
	});
	  
});

function copyClick(src, dst, e)
{
	$('#copy_path').val(src); $('#copyfilename').attr('value',dst); $('#copy-file').modal({show: true}); e.preventDefault(); e.stopPropagation();
}
function renameClick(path, name, e)
{
	$('#rename_path').val(path); $('#newfilename').attr('value',name); $('#rename-file').modal({show: true}); e.preventDefault(); e.stopPropagation();
}
function deleteClick(path, e)
{
	$('#delete_path').val(path); $('#delete-confirm').modal({show: true}); e.preventDefault(); e.stopPropagation();
}
function deleteDirClick(path, e)
{
	$('#delete_dir_path').val(path); $('#delete-dir-confirm').modal({backdrop: 'static', show: true}); event.preventDefault(); event.stopPropagation();
}

