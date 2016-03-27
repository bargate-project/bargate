$(document).ready(function($)
{
	/* Popup error modal show, if any */
	$('#popup-error').modal('show');

	/* Activate tooltips and enable hiding on clicking */
	$('[rel="tooltip"]').tooltip({"delay": { "show": 600, "hide": 100 }, "placement": "bottom", "trigger": "hover"});
	$('[rel="tooltip').on('mouseup', function () {$(this).tooltip('hide');});

	/* allow clickable opens without an <a> */
	$(".entry-open").click(function()
	{
		window.document.location = $(this).closest('.entry-click').data('url');
	});
	
});

/* Center modals */
$(function()
{

	function reposition()
	{
		var modal = $(this),
		dialog = modal.find('.modal-dialog');
		modal.css('display', 'block');
		// Dividing by two centers the modal exactly, but dividing by three 
		// or four works better for larger screens.
		dialog.css("margin-top", Math.max(0, ($(window).height() - dialog.height()) / 3));

	}

	$('.modal').on('show.bs.modal', reposition);
	$(window).on('resize', function(){$('.modal:visible').each(reposition);});
});
