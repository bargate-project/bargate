$(document).ready(function()
{
	var $container = $('#files').isotope(
	{
		getSortData:
		{
			name: '[data-filename]',
			type: '[data-raw-mtype]',
			mtime: '[data-raw-mtime] parseInt',
			size: '[data-raw-size] parseInt',
		},
		transitionDuration: '0.2s',
		percentPosition: true,
		sortAscending:
		{
			name: true,
			type: true,
			mtime: false,
			size: false
		},
		sortBy: 'name',
	});

	/* sort entries in a directory */
	$('.dir-sortby-name').on( 'click', function()
	{
		$container.isotope({ sortBy: 'name' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-name span').removeClass('invisible');
	});
	$('.dir-sortby-mtime').on( 'click', function()
	{
		$container.isotope({ sortBy: 'mtime' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-mtime span').removeClass('invisible');
	});
	$('.dir-sortby-type').on( 'click', function()
	{
		$container.isotope({ sortBy: 'type' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-type span').removeClass('invisible');
	});
	$('.dir-sortby-size').on( 'click', function()
	{
		$container.isotope({ sortBy: 'size' });
		$('.sortby-check').addClass('invisible');
		$('.dir-sortby-size span').removeClass('invisible');
	});

	var $dirs = $('#dirs').isotope(
	{
		getSortData: { name: '[data-filename]',},
		sortBy: 'name',
	});

});
