$(function ()
{
    'use strict';
                
    $('#fileupload').fileupload(
    {
        url: '{{url_home}}',
        dataType: 'json',
        formData: [{name: '_csrf_token', value: '{{ csrf_token() }}'}, {name: 'action', value: 'jsonupload'}, {name: 'path', value: '{{pwd}}'}],
        done: function (e, data)
        {
            $.each(data.result.files, function (index, file)
            {
                if (file.error)
                {
                	$('<div class="alert alert-danger fade in"> <a data-dismiss="alert" class="close" href="#">×</a> ' + file.name + ' was not uploaded: ' + file.error + ' </div>').appendTo('#upload-files');
        		}
        		else
        		{
                	$('<div class="alert alert-success fade in"> <a data-dismiss="alert" class="close" href="#">×</a> ' + file.name + ' was uploaded succesfully </div>').appendTo('#upload-files');
        		}
        		
        		$('#upload-progress').addClass('hidden');
            });
        },
        progressall: function (e, data)
        {
            var progress = parseInt(data.loaded / data.total * 100, 10);
            $('#upload-progress .progress-bar').css
            (
                'width',
                progress + '%'
            );
        },
        start: function (e)
        {
        	$('#upload-file').modal()
            $('#upload-progress').removeClass('hidden');
        },
    }).prop('disabled', !$.support.fileInput)
        .parent().addClass($.support.fileInput ? undefined : 'disabled');
});