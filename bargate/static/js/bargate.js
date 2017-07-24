$(document).ready(function($)
{
	/* Activate tooltips and enable hiding on clicking */
	$('[rel="tooltip"]').tooltip({"delay": { "show": 600, "hide": 100 }, "placement": "bottom", "trigger": "hover"});
	$('[rel="tooltip"]').on('mouseup', function () {$(this).tooltip('hide');});
});
