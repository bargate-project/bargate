$(document).ready(function($)
{
	/* Popup error modal show, if any */
	$('#popup-error').modal('show');

	/* Activate tooltips and enable hiding on clicking */
	$('[rel="tooltip"]').tooltip({"delay": { "show": 600, "hide": 100 }, "placement": "bottom", "trigger": "hover"});
	$('[rel="tooltip"]').on('mouseup', function () {$(this).tooltip('hide');});

	/* allow clickable opens without an <a> */
	$(".entry-open").click(function()
	{
		window.document.location = $(this).closest('.entry-click').data('url');
	});
	
});
