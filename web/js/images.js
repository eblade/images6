$(function() {
    var scope = {
        mode: 'menu',
        last_mode: 'menu',
        offset: 0,
        focus: 0,
        showing_metadata: false,
        showing_copies: false,
    };

    var load_menu = function() {
        scope.mode = 'menu';
        $('#background')
            .show()
            .html('<div id="menu"></div>');
        load_picker();
        $.ajax({
            url: '/importer',
            success: function(data) {
                $.each(data.entries, function(index, trigger) {
                    $('#menu').append('<div id="menu_trig_' + trigger.name + '" class="overlay_button wide inline">import from ' + trigger.name + '</div>');
                    $('#menu_trig_' + trigger.name)
                        .click(function() {
                            $.ajax({
                                url: trigger.trig_url,
                                method: 'POST',
                                success: function(data) {
                                    monitor('/importer/status', 'importing', 'scanning', 'importing');
                                },
                                error: function(data) {
                                    alert('Error.');
                                },
                            });
                        });
                });
                $('#menu').append('<div id="menu_trig_purge" class="overlay_button wide inline">purge</div>');
                $('#menu_trig_purge')
                    .click(function() {
                        $.ajax({
                            url: '/purger/trig',
                            method: 'POST',
                            success: function(data) {
                                monitor('/purger/status', 'purging', 'reading', 'deleting');
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
        scope.mode = 'monitor';
        $('#background')
            .html('<h2>' + caption + '</h2>')
            //.append('<div id="menu_result"></div>')
            .append('<div class="progress_outer"><div id="progress"></div></div>')
            .append('<div id="menu_failure"></div>');
        var poll = function() {
            $.ajax({
                url: url,
                success: function(data) {
                    //$('#menu_result').html(data.status + ' (' + data.progress + '%)');
                    if (data.failed > 0) {
                        $('#menu_failure').html('<div class="result failure">' + data.failed + ' failed</div>');
                    }
                    $('#progress').css('width', data.progress + '%');
                    if (data.status === 'acquired' || data.status === before || data.status === active) {
                        window.setTimeout(function() { poll(); }, 1000);
                    } else {
                        $('#background').fadeOut(400)
                        $.wait(500).then(load_menu);
                    }
                },
                error: function(data) {
                    scope.mode = 'menu';
                },
            });
        };
        poll();
    };

    var load_day = function(params) {
        scope.mode = 'day';
        $('#day_view').show();
        params = params || Object();
        var date = params.date || 'today';
        var delta = params.delta || '0';
        scope.focus = 0;
        $.ajax({
            url: '/entry?date=' + date + '&delta=' + delta,
            success: function(data) {
                date = data.date;
                if (data.next_date !== null) {
                    next = { date: data.next_date };
                } else {
                    next = { date: date, delta: 1 };
                }
                if (data.previous_date !== null) {
                    previous = { date: data.previous_date };
                } else {
                    previous = { date: date, delta: -1 };
                }
                $('#day_view')
                    .html('<div class="day">' +
                              '<div id="day_prevday" class="overlay_button">&lt;&lt;</div>' +
                              '<div id="day_purge" class="overlay_button">purge</div>' +
                              '<div id="day_back" class="overlay_button">back</div>' +
                          '</div><div id="day_more_buttons">' +
                              '<div id="day_nextday" class="overlay_button">&gt;&gt;</div>' +
                          '</div>' +
                          '</div>' +
                          '<div id="day_info">' +
                              '<div id="day_thisday" class="overlay_button">' + date + '</div>' +
                              '<div id="day_details"></div>' +
                              '<div id="date_info">' +
                                  '<input id="date_info_short" data-url="/date/' + date + '" data-name="short"/>' +
                                  '<textarea id="date_info_full" data-url="/date/' + date + '" data-name="full"></textarea>' +
                              '</div>' +
                          '</div>');
                $('#day_today').click(function() { load_day({'date': 'today', 'delta': '0'}); });
                $('#day_prevday').click(function() { load_day(previous); });
                $('#day_thisday').click(function() { load_day({'date': date, 'delta': '0'}); });
                $('#day_nextday').click(function() { load_day(next); });
                $('#day_back').click(function() { hide_day(); });
                $('#day_purge').click(function() { purge_pending(); });
                $('#day_details')
                    .append(data.count + (data.count === 1 ? ' entry' : ' entries'));
                autoSave('#date_info_short');
                autoSave('#date_info_full');
                $.ajax({
                    url: '/date/' + date,
                    success: function(data) {
                        $('#date_info_short').val(data.short);
                        $('#date_info_full').html(data.full);
                    },
                    error: function(data) {
                    },
                })
                $.each(data.entries, function(index, entry) {
                    $('#day_view')
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

    var load_picker = function(params) {
        $.ajax({
            url: '/date',
            success: function(data) {
                var last_month = "";
                var this_month = "";
                var last_year = "";
                var this_year = "";
                $.each(data.entries, function(index, date) {
                    this_month = ("" + date.date).substring(0, 7);
                    this_year = ("" + date.date).substring(0, 4);
                    if (this_year !== last_year) {
                        last_month = '';
                        last_year = this_year;
                        $('#background').append('<div class="year">' + this_year + '</div>');
                    }
                    if (this_month !== last_month) {
                        var month = {
                            '01': 'january',
                            '02': 'february',
                            '03': 'march',
                            '04': 'april',
                            '05': 'may',
                            '06': 'june',
                            '07': 'july',
                            '08': 'august',
                            '09': 'september',
                            '10': 'october',
                            '11': 'november',
                            '12': 'december',
                        }[("" + date.date).substring(5, 7)];
                        $('#background').append('<h2>' + month + '</h2>');
                    }
                    last_month = this_month;
                    var day = ("" + date.date).substring(8, 10);
                    var day_id = 'day-' + date.date;
                    var date_css = 'normal';
                    if (date.count === 0) {
                        date_css = 'empty';
                    } else if (date.count_per_state.pending > 0) {
                        date_css = 'pending';
                    } else if (date.count_per_state.purge > 0) {
                        date_css = 'purge';
                    }
                    if (date.short) {
                        $('#background')
                            .append('<div class="date_large">' +
                                    '<div id="' + day_id +
                                        '" data-date="' + date.date +
                                        '" class="date_block ' + date_css + '">' + day + '</div>' +
                                    '<div class="date_large_short">' + date.short + '</div></div>');
                    } else {
                        $('#background')
                            .append('<div id="' + day_id +
                                    '" data-date="' + date.date +
                                    '" class="date_block ' + date_css + '">' + day + '</div>');
                    }
                    $('#background')
                        .find('#' + day_id)
                        .click(function() {
                            load_day({ date: this.getAttribute('data-date') });
                        });
                });
            },
            error: function(data) {
                $('#background').append('<div class="failure">Errorz.</div>');
            },
        });
    };

    var update_focus = function(params) {
        params = params || new Object();
        var move = params.move || 0;
        var focus = params.focus;

        if (focus === undefined) {
            scope.focus += move;
        } else if (focus === -1) {
            scope.focus = scope.total_count - 1;
        } else {
            scope.focus = focus;
        }

        if (scope.focus < 0) {
            scope.focus = 0;
        } else if (scope.focus >= scope.total_count) {
            scope.focus = scope.total_count - 1;
        }

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
                $('#day_view').animate({
                    top: -$(thumb).position().top + 270,
                }, 200);
            } else {
                $(thumb).removeClass('selected');
            }
        });
    };

    var purge_pending = function() {
        $('.thumb').each(function(index, thumb) {
            var state = thumb.getAttribute('data-state');
            if (state == 'pending') {
                var url = thumb.getAttribute('data-state-url');
                $.ajax({
                    url: url + '?state=purge&soft=yes',
                    method: 'PUT',
                    success: function(data) {
                        thumb.setAttribute('data-state', 'purge');
                    },
                    error: function(data) {
                        alert("Unabled to purge " + id);
                    },
                });
                $(thumb).addClass('purge');
            }
        });
        $('#day_thisday').click();
    };

    var show_viewer = function(params) {
        params = params || Object();
        var proxy_url = params.proxy_url;
        var animate = params.animate === undefined ? true : params.animate;

        $('#overlay_metadata').hide();
        $('#overlay_copies').hide();

        $('#overlay').css('background-image', 'url(' + proxy_url + ')');
        if (animate) {
            scope.last_mode = scope.mode;
            $('#overlay').fadeIn();
        }
        scope.mode = 'proxy';
        scope.showing_metadata = false;
        scope.showing_copies = false;
        sync_overlay_buttons();
    };

    var hide_day = function() {
        scope.mode = 'menu';
        $('#overlay').hide();
        $('#day_view').hide();
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
            $('#toggle_metadata').addClass('select').addClass('extend');
        } else {
            $('#toggle_metadata').removeClass('select').removeClass('extend');
        }
        if (scope.showing_copies) {
            $('#toggle_copies').addClass('select').addClass('extend');
        } else {
            $('#toggle_copies').removeClass('select').removeClass('extend');
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

    var toggle_metadata = function(showing_metadata) {
        if (showing_metadata === undefined) {
            scope.showing_metadata = !scope.showing_metadata;
        } else {
            scope.showing_metadata = showing_metadata;
        }
        if (scope.showing_metadata) {
            scope.showing_copies = false;
            $('#overlay_copies').fadeOut();
        }
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
                    var srow = function(key, value, patch_key, in_metadata) {
                        $(table).append('<tr><td>' + key + '</td><td><div id="erow_' + key +
                                        '" class="editable_row">' + value + '</div></td></tr>');
                        $('#erow_' + key)
                            .click(function() {
                                $('#metadata')
                                    .html('<h3>Edit ' + key + '</h3><input type="text" name="srow" value="' + value +
                                          '"/><br/><button id="srow_save">Save</button>');
                                $('#srow_save')
                                    .click(function() {
                                        var patch = {};
                                        patch[patch_key] = $('input[name="srow"]').val(),
                                        $.ajax({
                                            url: '/entry/' + data.id + (in_metadata ? '/metadata' : ''),
                                            method: 'patch',
                                            contentType: "application/json",
                                            data: JSON.stringify(patch),
                                            success: function(data) {
                                                toggle_metadata(true);
                                            },
                                            error: function(data) {
                                                $('#metadata').html('error');
                                            },
                                        });
                                    });
                            });
                    };
                    var crow = function(key, value, choices) {
                        $(table).append('<tr><td>' + key + '</td><td><div id="erow_' + key +
                                        '" class="editable_row">' + value + '</div></td></tr>');
                        $('#erow_' + key)
                            .click(function() {
                                $('#metadata')
                                    .html('<h3>Edit ' + key + '</h3><fieldset id="crow"><legend>Select a new value</legend></fieldset>');
                                $.each(choices, function(index, choice) {
                                    $('#crow')
                                        .append('<input type="radio" name="crow" value="' + choice +
                                                '" ' + (choice == value ? 'checked' : '') +  '/>' + choice + '</br>');
                                });
                                $('#metadata')
                                    .append('<button id="crow_save">Save</button>');
                                $('#crow_save')
                                    .click(function() {
                                        var patch = {};
                                        patch[key] = $('input[name="crow"]').val();
                                        $.ajax({
                                            url: '/entry/' + data.id + '/metadata',
                                            method: 'patch',
                                            contentType: "application/json",
                                            data: JSON.stringify(patch),
                                            success: function(data) {
                                                toggle_metadata(true);
                                            },
                                            error: function(data) {
                                                $('#metadata').html('error');
                                            },
                                        });
                                    });
                            });
                    };
                    srow('Title', data.title, 'title', false);
                    srow('Description', data.description, 'description', false);
                    srow('Artist', data.metadata.Artist, 'Artist', true);
                    row('Taken', data.metadata.DateTimeOriginal);
                    row('Digitized', data.metadata.DateTimeDigitized);
                    if (data.metadata.FNumber[0] === 0) {
                        row('Aperture', 'unknown');
                    } else {
                        row('Aperture', 'F ' + data.metadata.FNumber[0] + ' / ' + data.metadata.FNumber[1]);
                    }
                    row('ISO', data.metadata.ISOSpeedRatings);
                    row('Focal length', data.metadata.FocalLength[0] + ' / ' + data.metadata.FocalLength[1]);
                    row('35mm equiv.', data.metadata.FocalLengthIn35mmFilm);
                    row('Geometry', data.metadata.Geometry[0] + ' x ' + data.metadata.Geometry[1]);
                    row('Colorspace', data.metadata.ColorSpace);
                    row('Exposure', data.metadata.ExposureTime[0] + ' / ' + data.metadata.ExposureTime[1]);
                    srow('Angle', data.metadata.Angle, 'Angle', true);
                    row('Flash', data.metadata.Flash);
                    row('ID', data.id);
                    srow('Copyright', data.metadata.Copyright, 'Copyright', true);
                    row('Folder', data.import_folder);
                    row('Filename', data.original_filename);
                    row('State', data.state);
                },
                error: function(data) {
                    $('#metadata').html('no metadata, apparently');
                },
            });
        } else {
            $('#overlay_metadata').fadeOut();
        }

    };

    var toggle_copies = function() {
        scope.showing_copies = !scope.showing_copies;
        if (scope.showing_copies) {
            scope.showing_metadata = false;
            $('#overlay_metadata').fadeOut();
        }
        sync_overlay_buttons();
        if (scope.showing_copies === true) {
            var thumb = $('img.thumb')[scope.focus];
            var url = thumb.getAttribute('data-self-url');
            $('#overlay_copies').fadeIn();
            $('#copies').html('loading...');
            $.ajax({
                url: url,
                success: function(data) {
                    $('#copies').html('');

                    var has_original = false,
                        has_proxy = false,
                        has_raw = false,
                        has_flickr = false;

                    var copy = function(key, style, callback) {
                        var id = 'copy_' + key;
                        $('#copies')
                            .append('<div class="copy ' + style + '" id="' + id + '">' + key + '</div>');

                        if (callback) {
                            $('#' + id).click(callback);
                        }
                    };

                    $.each(data.variants, function(index, variant) {
                        if (variant.purpose === 'original') { has_original = true; }
                        if (variant.purpose === 'proxy') { has_proxy = true; }
                        if (variant.purpose === 'raw') { has_raw = true; }
                    });

                    if (has_original) {
                        copy('original', 'download', function() {
                            location.href = data.original_url + '?download=yes';
                        });
                    }
                    if (has_proxy) {
                        copy('proxy', 'download', function() {
                            location.href = data.proxy_url + '?download=yes';
                        });
                    } else if (has_original) {
                        copy('proxy', 'none', function() {
                            $.ajax({
                                url: '/plugin/imageproxy/trig',
                                method: 'post',
                                contentType: "application/json",
                                data: JSON.stringify({
                                    '*schema': 'ImageProxyOptions',
                                    entry_id: data.id,
                                }),
                                success: function(data) {
                                    $('#copy_proxy').html('creating');
                                },
                                error: function(data) {
                                    $('#copy_proxy').html('error');
                                },
                            });
                        });
                    }
                    if (has_raw) {
                        copy('raw', 'download', function() {
                            location.href = data.raw_url + '?download=yes';
                        });
                    } else {
                        copy('raw', 'none', function() {
                            $.ajax({
                                url: '/plugin/rawfetch/trig',
                                method: 'post',
                                contentType: "application/json",
                                data: JSON.stringify({
                                    '*schema': 'RawFetchOptions',
                                    entry_id: data.id,
                                }),
                                success: function(data) {
                                    $('#copy_raw').html('fetching');
                                },
                                error: function(data) {
                                    $('#copy_raw').html('error');
                                },
                            });
                        });
                    }

                    $.each(data.backups, function(index, backup) {
                        if (backup.method === 'flickr') {
                            has_flickr = true;
                            //copy('flickr', 'next', function() { alert(backup.key); });
                        }
                    });

                    copy('flickr', has_flickr ? 'next' : 'none', function() {
                        $.ajax({
                            url: '/plugin/flickr/trig',
                            method: 'post',
                            contentType: "application/json",
                            data: JSON.stringify({
                                '*schema': 'FlickrOptions',
                                entry_id: data.id,
                            }),
                            success: function(data) {
                                $('#copy_flickr').html('sent');
                            },
                            error: function(data) {
                                $('#copy_flickr').html('error');
                            },
                        });
                    });
                },
                error: function(data) {
                    $('#copies').html('Error!');
                },
            });
        } else {
            $('#overlay_copies').fadeOut();
        }

    };

    $('#overlay_close').click(function() { hide_viewer(); });
    $('#overlay_keep').click(function() { keep(scope.focus); });
    $('#overlay_purge').click(function() { purge(scope.focus); });
    $('#toggle_metadata').click(function() { toggle_metadata(); });
    $('#toggle_copies').click(function() { toggle_copies(); });
    $('#overlay_check').click(function() { show_check(); });
    $('#overlay_proxy').click(function() { show_proxy(); });

    var bind_keys = function() {
        $(document).keydown(function(event) {
            if ($('input,textarea').is(':focus')) {
                // let it be
            } else if (scope.mode !== 'menu') {
                if (event.which === 37) { // left
                    update_focus({move: -1});
                    event.preventDefault();
                } else if (event.which === 39) { // right
                    update_focus({move: +1});
                    event.preventDefault();
                } else if (event.which === 38) { // up
                    update_focus({move: -10});
                    event.preventDefault();
                } else if (event.which === 40) { // down
                    update_focus({move: +10});
                    event.preventDefault();
                } else if (event.which === 36) { // home
                    update_focus({focus: 0});
                    event.preventDefault();
                } else if (event.which === 35) { // end
                    update_focus({focus: -1});
                    event.preventDefault();
                } else if (event.which === 27) { // escape
                    if (scope.mode === 'day') {
                        hide_day();
                    } else if (scope.mode === 'proxy') {
                        if (scope.showing_metadata) {
                            toggle_metadata();
                        } else if (scope.showing_copies) {
                            toggle_copies();
                        } else {
                            hide_viewer();
                        }
                    }
                } else if (event.which === 13) { // return
                    if (scope.mode === 'day') {
                        var thumb = $('img.thumb')[scope.focus];
                        show_viewer({
                            proxy_url: thumb.getAttribute('data-proxy-url'),
                        });
                        event.preventDefault();
                    }
                } else if (event.which === 77) { // m
                    toggle_metadata();
                } else if (event.which === 70) { // f
                    toggle_copies();
                } else if (event.which === 75) { // k
                    keep(scope.focus);
                } else if (event.which === 88) { // x
                    purge(scope.focus);
                } else if (event.which === 80) { // p
                    show_proxy();
                } else if (event.which === 67) { // c
                    show_check();
                }
            }
        });
    };

    $.wait = function(ms) {
        var defer = $.Deferred();
        setTimeout(function() { defer.resolve(); }, ms);
        return defer;
    };

    var autoSave = function (id) {
        $(id).change(function () {
            $(id).removeClass('error').addClass('saving');
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
                    $(id).removeClass('saving');
                },
                error: function (data) {
                    $(id).removeClass('saving').addClass('error');
                },
            });
        })
    };

    hide_day();
    hide_viewer();

    $.Images = $.Images || {};
    $.Images.bind_keys = bind_keys;
    $.Images.load_menu = load_menu;
});
