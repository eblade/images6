$(function() {
    var autosave = function (id) {
        $(id).change(function () {
            $(id).removeClass('autosave_error').addClass('autosave_saving');
            var url = $(id)[0].getAttribute('data-url');
            var field = $(id)[0].getAttribute('data-name');
            var data = new Object();
            data['only'] = field;
            data[field] = $(id).val();
            $.ajax({
                url: url,
                method: 'PUT',
                contentType: "application/json",
                data: JSON.stringify(data),
                success: function (data) {
                    $(id).removeClass('autosave_saving');
                },
                error: function (data) {
                    $(id).removeClass('autosave_saving').addClass('autosave_error');
                },
            });
        })
    };

    $.Images = $.Images || {};
    $.Images.autosave = autosave;
});
