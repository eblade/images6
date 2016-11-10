$(function() {
    $(document)
        .ready(function() {
            $.Images.bind_keys();
            $(window)
                .hashchange(function() {
                    $.Images.load_tag({
                        date: document.location.hash.substr(1),
                    });
                });
            $.Images.load_tag({
                date: document.location.hash.substr(1),
                override: true,
            });
        });
});
