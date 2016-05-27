$(function() {
    var scope = {
        mode: 'menu',
        offset: 0,
    };

    var clear = function(mode) {
        scope.mode = mode;
        $('#content').html('<div id="' + mode + '"></div>');
    };

    var load_menu = function() {
        clear('menu');
        $('#menu')
            .append('<h2>Browse</h2>')
            .append('<div id="menu_browse" class="menu_section"></div>')
            .append('<h2>Import</h2>')
            .append('<div id="menu_trig" class="menu_section"></div>');
        $.ajax({
            url: '/importer',
            success: function(data) {
                $('#menu_trig').html('');
                $.each(data.entries, function(index, trigger) {
                    $('#menu_trig').append('<button id="menu_trig_' + trigger.name + '">Import from ' + trigger.name + '</button><br/>');
                    $('#menu_trig_' + trigger.name)
                        .button()
                        .click(function() {
                            $.ajax({
                                url: trigger.trig_url,
                                method: 'POST',
                                success: function(data) {
                                    monitor_import();
                                },
                                error: function(data) {
                                    alert('Error.');
                                },
                            });
                        });
                });
            },
        });
        $('#menu_browse')
            .append('<button>Browse</button>')
            .find('button')
            .button()
            .click(function() {
                load_browse();
            });
    };

    var monitor_import = function() {
        clear('menu');
        $('#menu')
            .append('<h2>Working</h2>')
            .append('<div id="menu_trig" class="menu_section"></div>');
        $.ajax({
            url: '/importer/status',
            success: function(data) {
                $('#menu_trig').html('<div class="result">' + data.status + ' (' + data.progress + '%)</div>');
                if (data.failed > 0) {
                    $('#menu_trig').append('<div class="result failure">' + data.failed + ' failed</div>');
                }
                if (data.status === 'acquired' || data.status === 'scanning' || data.status === 'importing') {
                    window.setTimeout(monitor_import, 1000);
                } else {
                    $('#menu_trig')
                        .append('<br/><button>Fantastic</button>')
                        .find('button')
                        .button()
                        .click(function() {
                            load_menu();
                        });
                }
            },
            error: function(data) {
            },
        });
    };

    var load_browse = function(params) {
        params = params || Object();
        var offset = params.offset || 0;
        var page_size = params.offset || 20;
        if (offset === 0) {
            clear('browse');
        }
        $.ajax({
            url: '/entry?offset=' + offset + '&page_size=' + page_size,
            success: function(data) {
                $.each(data.entries, function(index, entry) {
                    $('#browse').append('<img class="thumb" src="' + entry.thumb_url + '"/>');
                });
            }
        });
        scope.offset = offset + page_size;
    };

    $(window).scroll(function() {
        if (scope.mode === 'browse') {
            if ($(window).scrollTop() == $(document).height() - $(window).height()) {
                load_browse({
                    offset: scope.offset,
                    page_size: 100,
                });
            }
        }
    });

    load_menu();
});
