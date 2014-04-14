/* BARGATE LOCAL JAVASCRIPT */

/* Popup error modal show, if any */
$(document).ready(function(){
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

$(document).ready(function($)
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

$(document).ready(function() {
	$('#create-directory').on('shown.bs.modal', function() {
		$('#create-directory input[type="text"]').focus();
	});

	$('.copy').click(function()
	{
		var parentRow = $(this).closest(".rowclick-tr");
		$('#copy_path').val(parentRow.attr('data-path'));
		$('#copyfilename').attr('value',"Copy of " + parentRow.attr('data-filename'));
		$('#copy-file').modal({show: true});
		$('#copyfilename').focus();
		event.preventDefault();
		event.stopPropagation();
	});

	$('.rename').click(function()
	{
		var parentRow = $(this).closest(".rowclick-tr");
		$('#rename_path').val(parentRow.attr('data-path'));
		$('#newfilename').attr('value',parentRow.attr('data-filename'));
		$('#rename-file').modal({show: true});
		$('#newfilename').focus();
		event.preventDefault();
		event.stopPropagation();
	});

	$('.del').click(function()
	{
		var parentRow = $(this).closest(".rowclick-tr");
		$('#delete_path').val(parentRow.attr('data-path'));
		$('#delete-confirm').modal({show: true});
		event.preventDefault();
		event.stopPropagation();
	});

	$('.delDir').click(function()
	{
		var parentRow = $(this).closest(".rowclick-tr");
		$('#delete_dir_path').val(parentRow.attr('data-path'));
		$('#delete-dir-confirm').modal({backdrop: 'static', show: true});
		event.preventDefault();
		event.stopPropagation();
	});
});
