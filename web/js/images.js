$(function() {
    var scope = {
        mode: 'menu',
        last_mode: 'menu',
        offset: 0,
        focus: 0,
        showing_metadata: false,
    };

    var clear = function(mode) {
        scope.mode = mode;
        document.title = '*' + scope.mode;
        $('#content').html('<div id="' + mode + '"></div>');
    };

    var load_menu = function() {
        clear('menu');
        $('#menu')
            .append('<h2>Browse</h2>')
            .append('<div id="menu_browse" class="menu_section"></div>')
            .append('<h2>Import/Purge</h2>')
            .append('<div id="menu_trig" class="menu_section"></div>');
        $.ajax({
            url: '/importer',
            success: function(data) {
                $('#menu_trig').html('');
                $.each(data.entries, function(index, trigger) {
                    $('#menu_trig').append('<div id="menu_trig_' + trigger.name + '" class="overlay_button wide">Import from ' + trigger.name + '</div>');
                    $('#menu_trig_' + trigger.name)
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
                $('#menu_trig').append('<div id="menu_trig_purge" class="overlay_button wide">Purge</div>');
                $('#menu_trig_purge')
                    .click(function() {
                        $.ajax({
                            url: '/purger/trig',
                            method: 'POST',
                            success: function(data) {
                                monitor_purge();
                            },
                            error: function(data) {
                                alert('Error.');
                            },
                        });
                    });
            },
        });
        $('#menu_browse')
            .append('<div id="browse_button" class="overlay_button wide">Browse</div>')
            .find('#browse_button')
            .click(function() {
                load_browse();
            });
        $('#menu_browse')
            .append('<div id="day_button" class="overlay_button wide">Day</div>')
            .find('#day_button')
            .click(function() {
                load_day();
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

    var monitor_purge = function() {
        clear('menu');
        $('#menu')
            .append('<h2>Working</h2>')
            .append('<div id="menu_trig" class="menu_section"></div>');
        $.ajax({
            url: '/purger/status',
            success: function(data) {
                $('#menu_trig').html('<div class="result">' + data.status + ' (' + data.progress + '%)</div>');
                if (data.failed > 0) {
                    $('#menu_trig').append('<div class="result failure">' + data.failed + ' failed</div>');
                }
                if (data.status === 'acquired' || data.status === 'reading' || data.status === 'deleting') {
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
        scope.mode = 'browse';
        params = params || Object();
        var offset = params.offset || 0;
        var page_size = params.page_size || 20;
        if (offset === 0) {
            clear('browse');
            $('#browse').append('<div class="debug">total=<span id="scope_total_count"></span>, focus=<span id="scope_focus"></span>, offset=<span id="scope_offset"></span>');
            scope.offset = 0;
            scope.focus = 0;
            scope.total_count = 0;
        }
        $.ajax({
            url: '/entry?offset=' + offset + '&page_size=' + page_size,
            success: function(data) {
                $.each(data.entries, function(index, entry) {
                    real_index = offset + index;
                    $('#browse')
                        .append('<img data-self-url="' + entry.self_url +
                                '" data-state="' + entry.state +
                                '" data-state-url="' + entry.state_url +
                                '" data-check-url="' + entry.check_url +
                                '" data-proxy-url="' + entry.proxy_url +
                                '" class="thumb" id="thumb_' + real_index +
                                '" src="' + entry.thumb_url +
                                '" title="' + real_index + '"/>');
                    $('#thumb_' + real_index)
                        .click(function(event) {
                            var id = parseInt(this.title);
                            var thumb = $('img.thumb')[id]
                            update_focus({focus: id});
                            show_viewer({
                                proxy_url: thumb.getAttribute('data-proxy-url'),
                            });
                        });
                });
                if (offset === 0) {
                    update_focus({focus: 0});
                }
                scope.offset = offset + data.count;
                scope.total_count += data.count;
            },
        });
    };

    var load_day = function(params) {
        scope.mode = 'day';
        params = params || Object();
        var date = params.date || 'today';
        var delta = params.delta || '0';
        clear('day');
        scope.focus = 0;
        $.ajax({
            url: '/entry?date=' + date + '&delta=' + delta,
            success: function(data) {
                date = data.date;
                $('#day')
                    .append('<div id="date" class="date"><span id="yesterday">&lt;&lt;</span> ' + date + ' <span id="tomorrow">&gt;&gt;</span></div>');
                $('#yesterday')
                    .click(function() {
                        load_day({'date': date, 'delta': '-1'});
                    });
                $('#tomorrow')
                    .click(function() {
                        load_day({'date': date, 'delta': '1'});
                    });
                $('#day')
                    .append('<div class="date_spacer"> </div>');
                $.each(data.entries, function(index, entry) {
                    $('#day')
                        .append('<img data-self-url="' + entry.self_url +
                                '" data-state="' + entry.state +
                                '" data-state-url="' + entry.state_url +
                                '" data-check-url="' + entry.check_url +
                                '" data-proxy-url="' + entry.proxy_url +
                                '" class="thumb ' + entry.state + '" id="thumb_' + index +
                                '" src="' + entry.thumb_url +
                                '" title="' + index + '"/>');
                    $('#thumb_' + index)
                        .click(function(event) {
                            var id = parseInt(this.title);
                            var thumb = $('img.thumb')[id]
                            update_focus({focus: id});
                            show_viewer({
                                proxy_url: thumb.getAttribute('data-proxy-url'),
                            });
                        });
                });
                update_focus({focus: 0});
                scope.total_count = data.count;
            },
        });
    };

    var update_focus = function(params) {
        params = params || new Object();
        var move = params.move || 0;
        var focus = params.focus;

        if (focus === undefined) {
            scope.focus += move;
        } else {
            scope.focus = focus;
        }

        if (scope.focus < 0) {
            scope.focus = 0;
        } else if (scope.focus >= scope.total_count) {
            scope.focus = scope.total_count - 1;
        }

        $('#scope_total_count').html(scope.total_count);
        $('#scope_focus').html(scope.focus);
        $('#scope_offset').html(scope.offset);

        $('.thumb').each(function(index, thumb) {
            if (index === scope.focus) {
                if (scope.mode === 'check') {
                    scope.mode = 'proxy';
                }
                if (scope.mode === 'proxy') {
                    show_viewer({
                        proxy_url: thumb.getAttribute('data-proxy-url'),
                        animate: false,
                    });
                }
                $(thumb).addClass('selected');
                $('html, body').animate({
                    scrollTop: $(thumb).offset().top - 200,
                }, 200);
            } else {
                $(thumb).removeClass('selected');
            }
        });


    };

    var show_viewer = function(params) {
        params = params || Object();
        var proxy_url = params.proxy_url;
        var animate = params.animate === undefined ? true : params.animate;

        $('#overlay_metadata').hide();

        $('#overlay').css('background-image', 'url(' + proxy_url + ')');
        if (animate) {
            scope.last_mode = scope.mode;
            $('#overlay').fadeIn();
        }
        scope.mode = 'proxy';
        scope.showing_metadata = false;
        sync_overlay_buttons();
    };

    var hide_viewer = function() {
        scope.mode = scope.last_mode;
        $('#overlay').hide();
    };

    var sync_overlay_buttons = function() {
        var thumb = $('img.thumb')[scope.focus];
        var state = thumb.getAttribute('data-state');
        if (state === 'keep') {
            $('#overlay_keep').addClass('keep');
        } else {
            $('#overlay_keep').removeClass('keep');
        }
        if (state === 'purge') {
            $('#overlay_purge').addClass('purge');
        } else {
            $('#overlay_purge').removeClass('purge');
        }
        if (scope.mode === 'proxy') {
            $('#overlay_proxy').addClass('select');
            $('#overlay_check').removeClass('select');
        } else if (scope.mode === 'check') {
            $('#overlay_check').addClass('select');
            $('#overlay_proxy').removeClass('select');
        }
        if (scope.showing_metadata) {
            $('#overlay_meta').addClass('select').addClass('extend');
        } else {
            $('#overlay_meta').removeClass('select').removeClass('extend');
        }
    };

    var keep = function(id) {
        var thumb = $('img.thumb')[id];
        var url = thumb.getAttribute('data-state-url');
        $.ajax({
            url: url + '?state=keep',
            method: 'PUT',
            success: function(data) {
                thumb.setAttribute('data-state', 'keep');
                sync_overlay_buttons();
            },
            error: function(data) {
                alert("Unabled to keep " + id);
            },
        });
    };

    var purge = function(id) {
        var thumb = $('img.thumb')[id];
        var url = thumb.getAttribute('data-state-url');
        $.ajax({
            url: url + '?state=purge',
            method: 'PUT',
            success: function(data) {
                thumb.setAttribute('data-state', 'purge');
                sync_overlay_buttons();
            },
            error: function(data) {
                alert("Unabled to purge " + id);
            },
        });
    };

    var show_check = function() {
        var thumb = $('img.thumb')[scope.focus];
        var url = thumb.getAttribute('data-check-url');
        $('#overlay').css('background-image', 'url(' + url + ')');
        scope.mode = 'check';
        sync_overlay_buttons();
    };

    var show_proxy = function() {
        var thumb = $('img.thumb')[scope.focus];
        var url = thumb.getAttribute('data-proxy-url');
        $('#overlay').css('background-image', 'url(' + url + ')');
        scope.mode = 'proxy';
        sync_overlay_buttons();
    };

    var toggle_metadata = function() {
        scope.showing_metadata = !scope.showing_metadata;
        sync_overlay_buttons();
        if (scope.showing_metadata === true) {
            var thumb = $('img.thumb')[scope.focus];
            var url = thumb.getAttribute('data-self-url');
            $('#overlay_metadata').fadeIn();
            $('#metadata').html('loading...');
            $.ajax({
                url: url,
                success: function(data) {
                    var table = $('#metadata')
                        .html('<table></table>')
                        .find('table');
                    var row = function(key, value) {
                        $(table).append('<tr><td>' + key + '</td><td>' + value + '</td></tr>');
                    };
                    row('Artist', data.metadata.Artist);
                    row('Copyright', data.metadata.Copyright);
                    row('Taken', data.metadata.DateTimeOriginal);
                    row('Digitized', data.metadata.DateTimeDigitized);
                    row('Colorspace', data.metadata.ColorSpace);
                    row('Exposure time', data.metadata.ExposureTime[0] + ' / ' + data.metadata.ExposureTime[1]);
                    if (data.metadata.FNumber[0] === 0) {
                        row('Aperture', 'unknown');
                    } else {
                        row('Aperture', 'F ' + data.metadata.FNumber[0] + ' / ' + data.metadata.FNumber[1]);
                    }
                    row('Focal length', data.metadata.FocalLength[0] + ' / ' + data.metadata.FocalLength[1]);
                    row('35mm equiv.', data.metadata.FocalLengthIn35mmFilm);
                    row('Geometry', data.metadata.Geometry[0] + ' x ' + data.metadata.Geometry[1]);
                    row('ISO', data.metadata.ISOSpeedRatings);
                    row('Flash', data.metadata.Flash);
                    row('ID', data.id);
                    row('State', data.state);
                    row('Import folder', data.import_folder);
                    row('Import filename', data.original_filename);
                },
                error: function(data) {
                    $('#metadata').html('no metadata, apparently');
                },
            });
        } else {
            $('#overlay_metadata').fadeOut();
        }

    };

    $('#overlay_close').click(function() { hide_viewer(); });
    $('#overlay_keep').click(function() { keep(scope.focus); });
    $('#overlay_purge').click(function() { purge(scope.focus); });
    $('#overlay_meta').click(function() { toggle_metadata(scope.focus); });
    $('#overlay_check').click(function() { show_check(); });
    $('#overlay_proxy').click(function() { show_proxy(); });

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

    $(document).keydown(function(event) {
        document.title = scope.mode + ' ' + event.which;
        if (event.which === 37) { // left
            update_focus({move: -1});
        } else if (event.which === 39) { // right
            update_focus({move: +1});
        } else if (event.which === 27) { // escape
            if (scope.mode === 'browse' || scope.mode === 'day') {
                load_menu();
            } else if (scope.mode === 'proxy') {
                if (scope.showing_metadata) {
                    toggle_metadata();
                } else {
                    hide_viewer();
                }
            }
        } else if (event.which === 13) { // return
            if (scope.mode === 'browse' || scope.mode === 'day') {
                var thumb = $('img.thumb')[scope.focus];
                show_viewer({
                    proxy_url: thumb.getAttribute('data-proxy-url'),
                });
            }
        }
        // right: 39
        // left: 37
        // up: 38
        // down: 40
    });

    load_menu();
    hide_viewer();
});
