$(function() {
    $(document)
        .ready(function() {
            $.Images.bind_keys();
            $(window)
                .hashchange(function() {
                    $.Images.load_date({
                        date: document.location.hash.substr(1) || 'today',
                    });
                });
            $.Images.load_date({
                date: document.location.hash.substr(1) || 'today',
                override: true,
            });
        });
});

