$( document ).ready(function() {
	$(".login-focus").focus();
	env = nunjucks.configure('',{ autoescape: true});
	$('[data-toggle="about"').click(function (e) {
		e.preventDefault();
		e.stopPropagation();
		$('#scr-c').html(nunjucks.render('modals/about.html', {}));
		$('#scr').modal('show');
	});
});
