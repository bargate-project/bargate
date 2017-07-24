function showError(title,desc) {
	$("#modal-error-title").text(title);
	$("#modal-error-desc").text(desc);
	$('#modal-error').modal('show');
}

$(document).ready(function($) {
	/* Activate tooltips and enable hiding on clicking */
	$('[rel="tooltip"]').tooltip({"delay": { "show": 600, "hide": 100 }, "placement": "bottom", "trigger": "hover"});
	$('[rel="tooltip"]').on('mouseup', function () {$(this).tooltip('hide');});
});
