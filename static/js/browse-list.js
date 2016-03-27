$(document).ready(function()
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
});
