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
        $('#content').html('<div id="' + mode + '"></div>');
    };

    var load_menu = function() {
        clear('menu');
        $('#menu')
            .append('<div id="day_button" class="overlay_button wide">browse</div>')
            .find('#day_button')
            .click(function() {
                load_day();
            });
        $.ajax({
            url: '/importer',
            success: function(data) {
                $.each(data.entries, function(index, trigger) {
                    $('#menu').append('<div id="menu_trig_' + trigger.name + '" class="overlay_button wide">import from ' + trigger.name + '</div>');
                    $('#menu_trig_' + trigger.name)
                        .click(function() {
                            $.ajax({
                                url: trigger.trig_url,
                                method: 'POST',
                                success: function(data) {
                                    monitor('/importer/status', 'importing...', 'scanning', 'importing');
                                },
                                error: function(data) {
                                    alert('Error.');
                                },
                            });
                        });
                });
                $('#menu').append('<div id="menu_trig_purge" class="overlay_button wide">purge</div>');
                $('#menu_trig_purge')
                    .click(function() {
                        $.ajax({
                            url: '/purger/trig',
                            method: 'POST',
                            success: function(data) {
                                monitor('/purger/status', 'purging...', 'reading', 'deleting');
                            },
                            error: function(data) {
                                alert('Error.');
                            },
                        });
                    });
            },
        });
    };

    var monitor = function(url, caption, before, active) {
        clear('menu');
        $('#menu')
            .append('<h2>' + caption + '</h2>')
            .append('<div id="menu_result"></div>')
            .append('<div class="progress_outer"><div id="progress"></div></div>')
            .append('<div id="menu_failure"></div>');
        $.ajax({
            url: '/importer/status',
            success: function(data) {
                $('#menu_result').html(data.status + ' (' + data.progress + '%)');
                if (data.failed > 0) {
                    $('#menu_failure').html('<div class="result failure">' + data.failed + ' failed</div>');
                }
                $('#progress').css('width', data.progress + '%');
                if (data.status === 'acquired' || data.status === before || data.status === active) {
                    window.setTimeout(monitor_import, 1000);
                } else {
                    $.wait(2000).then(load_menu);
                }
            },
            error: function(data) {
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
                    .html('<div class="day">' +
                          '<div id="day_today" class="overlay_button">today</div>' +
                          '<div id="day_prevday" class="overlay_button">prev</div>' +
                          '<div id="day_nextday" class="overlay_button">next</div>' +
                          '</div><div id="day_more_buttons">' +
                          '<div id="day_back" class="overlay_button">back</div>' +
                          '<div id="day_pick" class="overlay_button">pick</div>' +
                          '</div><div id="day_info">' +
                          '<div id="day_thisday" class="overlay_button">' + date + '</div>' +
                          '<div id="day_details"></div></div>');
                $('#day_today').click(function() { load_day({'date': 'today', 'delta': '0'}); });
                $('#day_prevday').click(function() { load_day({'date': date, 'delta': '-1'}); });
                $('#day_thisday').click(function() { load_day({'date': date, 'delta': '0'}); });
                $('#day_nextday').click(function() { load_day({'date': date, 'delta': '1'}); });
                $('#day_back').click(function() { load_menu(); });
                $('#day_pick').click(function() { load_picker(); });
                $('#day_details')
                    .append(data.count + ' entries');
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
                    scrollTop: $(thumb).offset().top - 400,
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

    $(document).keydown(function(event) {
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

    $.wait = function(ms) {
        var defer = $.Deferred();
        setTimeout(function() { defer.resolve(); }, ms);
        return defer;
    };

    load_menu();
    hide_viewer();
});
