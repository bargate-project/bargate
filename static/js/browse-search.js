$(document).ready(function()
{
	$('#dir').DataTable( {
		"paging": false,
		"searching": false,
		"info": false,
		"columns": [
			{ "orderable": false },
			{ "orderable": false },
		],
		"dom": 'lrtip'
	});
});
