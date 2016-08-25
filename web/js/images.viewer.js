$(function() {
    var
        feed_div = '#date_feed',
        scope = {
            offset: 0,
            focus: 0,
            showing_viewer: false,
            showing_metadata: false,
            showing_copies: false,
            mode:  'proxy',
            date: null,
        };

    var load_date = function(params) {
        params = params || Object();
        var date = params.date || 'today';
        var delta = params.delta || '0';
        var override = params.override || false;
        scope.focus = 0;
        if (document.location.hash !== '#' + date) {
            document.location.hash = '#' + date;
        } else if (!override) {
            return;
        }
        $.ajax({
            url: 'entry?date=' + date + '&delta=' + delta,
            success: function(data) {
                date = data.date;
                scope.date = date;
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
                $('#date_feed')
                    .html('');
                $('#date_this')
                    .html(date)
                    .click(function() { load_date({'date': 'today', 'delta': '0'}); });
                $('#date_prev')
                    .click(function() { load_date(previous); });
                $('#date_next')
                    .click(function() { load_date(next); });
                $('#date_back')
                    .click(function() { back_to_index(); });
                $('#date_purge')
                    .click(function() { purge_pending(); });
                $('#date_details')
                    .html(data.count + (data.count === 1 ? ' entry' : ' entries'));
                $.Images.autosave('#date_info_short');
                $.Images.autosave('#date_info_full');
                $.ajax({
                    url: '/date/' + date,
                    success: function(data) {
                        $('#date_info_short').val(data.short);
                        $('#date_info_short')[0].setAttribute('data-url', '/date/' + date);
                        $('#date_info_full').html(data.full);
                        $('#date_info_full')[0].setAttribute('data-url', '/date/' + date);
                    },
                    error: function(data) {
                    },
                })
                $.each(data.entries, function(index, entry) {
                    $('#date_feed')
                        .append('<img data-self-url="' + entry.self_url +
                                '" data-state="' + entry.state +
                                '" data-state-url="' + entry.state_url +
                                '" data-check-url="' + entry.check_url +
                                '" data-proxy-url="' + entry.proxy_url +
                                '" class="thumb date_state_' + entry.state + '" id="thumb_' + index +
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
                $(thumb).addClass('date_selected');
                $('#day_view').animate({
                    top: -$(thumb).position().top + 270,
                }, 200);
            } else {
                $(thumb).removeClass('date_selected');
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
                $(thumb).removeClass('date_state_pending');
                $(thumb).addClass('date_state_purge');
            }
        });
        $('#day_thisday').click();
    };

    var show_viewer = function(params) {
        params = params || Object();
        var proxy_url = params.proxy_url;
        var animate = params.animate === undefined ? true : params.animate;

        $('#viewer_metadata').hide();
        $('#viewer_copies').hide();

        $('#viewer_overlay').css('background-image', 'url(' + proxy_url + ')');
        if (animate) {
            $('#viewer_overlay').fadeIn();
        }
        scope.mode = 'proxy';
        scope.showing_viewer = true;
        scope.showing_metadata = false;
        scope.showing_copies = false;
        sync_overlay_buttons();
    };

    var back_to_index = function() {
        document.location = '/#' + scope.date;
    };

    var hide_viewer = function() {
        scope.showing_viewer = false;
        $('#viewer_overlay').hide();
    };

    var sync_overlay_buttons = function() {
        var thumb = $('img.thumb')[scope.focus];
        var state = thumb.getAttribute('data-state');
        if (state === 'keep') {
            $('#viewer_keep').addClass('toggle_state_keep');
        } else {
            $('#viewer_keep').removeClass('toggle_state_keep');
        }
        if (state === 'purge') {
            $('#viewer_purge').addClass('toggle_state_purge');
        } else {
            $('#viewer_purge').removeClass('toggle_state_purge');
        }
        if (scope.mode === 'proxy') {
            $('#viewer_proxy').addClass('toggle_selected');
            $('#viewer_check').removeClass('toggle_selected');
        } else if (scope.mode === 'check') {
            $('#viewer_check').addClass('toggle_selected');
            $('#viewer_proxy').removeClass('toggle_selected');
        }
        if (scope.showing_metadata) {
            $('#viewer_toggle_metadata').addClass('toggle_selected').addClass('toggle_extended');
        } else {
            $('#viewer_toggle_metadata').removeClass('toggle_selected').removeClass('toggle_extended');
        }
        if (scope.showing_copies) {
            $('#viewer_toggle_copies').addClass('toggle_selected').addClass('toggle_extended');
        } else {
            $('#viewer_toggle_copies').removeClass('toggle_selected').removeClass('toggle_extended');
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
                $(thumb).removeClass('date_state_pending');
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
                $(thumb).removeClass('date_state_pending');
                $(thumb).addClass('date_state_purge');
            },
            error: function(data) {
                alert("Unabled to purge " + id);
            },
        });
    };

    var show_check = function() {
        var thumb = $('img.thumb')[scope.focus];
        var url = thumb.getAttribute('data-check-url');
        $('#viewer_overlay').css('background-image', 'url(' + url + ')');
        scope.mode = 'check';
        sync_overlay_buttons();
    };

    var show_proxy = function() {
        var thumb = $('img.thumb')[scope.focus];
        var url = thumb.getAttribute('data-proxy-url');
        $('#viewer_overlay').css('background-image', 'url(' + url + ')');
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
            $('#viewer_copies').fadeOut();
        }
        sync_overlay_buttons();
        if (scope.showing_metadata === true) {
            var thumb = $('img.thumb')[scope.focus];
            var url = thumb.getAttribute('data-self-url');
            $('#viewer_metadata').fadeIn();
            $('#viewer_metadata_content').html('loading...');
            $.ajax({
                url: url,
                success: function(data) {
                    $('#viewer_metadata_content')
                        .html('');
                    var row = function(key, value) {
                        value = value || '-';
                        $('#viewer_metadata_content')
                            .append('<div class="viewer_metadata_key">' + key + '</div>' +
                                    '<div class="viewer_metadata_value">' + value + '</div>');
                    };
                    var srow = function(key, value, patch_key, in_metadata, valid_values) {
                        value = value === null ? '' : value;
                        var
                            url = '/entry/' + data.id + (in_metadata ? '/metadata' : ''),
                            id = 'autosave_' + patch_key;
                        $('#viewer_metadata_content')
                            .append('<div class="viewer_metadata_key">' + key + '</div>' +
                                    '<div class="viewer_metadata_editable">' +
                                    '<input id="' + id + '" value="' + value + '" ' +
                                           'data-url="' + url + '" ' +
                                           'data-name="' + patch_key + '"/></div>');
                        $.Images.autosave('#' + id, valid_values !== undefined ? function(value) {
                            return valid_values.indexOf(value) !== -1;
                        } : undefined);
                    };
                    row('ID', data.id);
                    srow('Title', data.title, 'title', false);
                    srow('Description', data.description, 'description', false);
                    srow('Artist', data.metadata.Artist, 'Artist', true);
                    row('Taken', data.metadata.DateTimeOriginal);
                    if (data.metadata.FNumber[0] === 0) {
                        row('Aperture', 'unknown');
                    } else {
                        row('Aperture', 'f' + data.metadata.FNumber[0] + '/' + data.metadata.FNumber[1]);
                    }
                    row('ISO', data.metadata.ISOSpeedRatings);
                    row('Focal length', data.metadata.FocalLength[0] + '/' + data.metadata.FocalLength[1]);
                    row('35mm equiv.', data.metadata.FocalLengthIn35mmFilm);
                    row('Geometry', data.metadata.Geometry[0] + ' x ' + data.metadata.Geometry[1]);
                    row('Exposure', data.metadata.ExposureTime[0] + '/' + data.metadata.ExposureTime[1]);
                    srow('Angle', data.metadata.Angle, 'Angle', true, ['-270', '-180', '-90', '0', '90', '180', '270']);
                    srow('Copyright', data.metadata.Copyright, 'Copyright', true);
                    row('Source', data.import_folder + '/' + data.original_filename);
                },
                error: function(data) {
                    $('#viewer_metadata_content').html('no metadata, apparently');
                },
            });
        } else {
            $('#viewer_metadata').fadeOut();
        }

    };

    var toggle_copies = function() {
        scope.showing_copies = !scope.showing_copies;
        if (scope.showing_copies) {
            scope.showing_metadata = false;
            $('#viewer_metadata').fadeOut();
        }
        sync_overlay_buttons();
        if (scope.showing_copies === true) {
            var thumb = $('img.thumb')[scope.focus];
            var url = thumb.getAttribute('data-self-url');
            $('#viewer_copies').fadeIn();
            $('#viewer_copies_content').html('loading...');
            $.ajax({
                url: url,
                success: function(data) {
                    $('#viewer_copies_content').html('');

                    var has_original = false,
                        has_proxy = false,
                        has_raw = false,
                        has_flickr = false;

                    var button = function(key, style, callback) {
                        var id = 'copy_' + key;
                        $('#viewer_copies_content')
                            .append('<div class="viewer_make_copy_button ' + style + '" id="' + id + '">' + key + '</div>');

                        if (callback) {
                            $('#' + id).click(callback);
                        }
                    };

                    var header = function(title) {
                        $('#viewer_copies_content')
                            .append('<h2>' + title + '</h2>');
                    }

                    var link = function(title, url) {
                        $('#viewer_copies_content')
                            .append('<a href="' + url + '">' + title + '</a></br>');
                    }

                    header('files');
                    $.each(data.variants, function(index, variant) {
                        if (variant.purpose === 'original') { has_original = true; }
                        if (variant.purpose === 'proxy') { has_proxy = true; }
                        if (variant.purpose === 'raw') { has_raw = true; }

                        if (variant.purpose === variant.source_purpose && variant.version === variant.source_version) {
                            link(variant.purpose + '/' + variant.version, data.urls[variant.purpose][variant.version]);
                        } else {
                            link(variant.purpose + '/' + variant.version + ' (of ' +
                                 variant.source_purpose + '/' + variant.source_version + ')',
                                 data.urls[variant.purpose][variant.version]);
                        }
                    });

                    header('actions');
                    if (has_original) {
                        button('proxy', 'none', function() {
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
                    if (!has_raw) {
                        button('raw', 'none', function() {
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
                        }
                    });

                    button('flickr', has_flickr ? 'next' : 'none', function() {
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
                    $('#viewer_copies_content').html('Error!');
                },
            });
        } else {
            $('#viewer_copies').fadeOut();
        }

    };

    $('#viewer_keep').click(function() { keep(scope.focus); });
    $('#viewer_purge').click(function() { purge(scope.focus); });
    $('#viewer_toggle_metadata').click(function() { toggle_metadata(); });
    $('#viewer_toggle_copies').click(function() { toggle_copies(); });
    $('#viewer_check').click(function() { show_check(); });
    $('#viewer_proxy').click(function() { show_proxy(); });
    $('#viewer_close').click(function() { hide_viewer(); });

    var bind_keys = function() {
        $(document).keydown(function(event) {
            if ($('input,textarea').is(':focus')) {
                // let it be
            } else {
                if (event.which === 37) { // left
                    update_focus({move: -1});
                    event.preventDefault();
                } else if (event.which === 39) { // right
                    update_focus({move: +1});
                    event.preventDefault();
                } else if (event.which === 36) { // home
                    update_focus({focus: 0});
                    event.preventDefault();
                    } else if (event.which === 35) { // end
                        update_focus({focus: -1});
                        event.preventDefault();
                } else if (scope.showing_viewer === false) {
                    if (event.which === 27) { // escape
                        back_to_index();
                        event.preventDefault();
                    } else if (event.which === 13) { // return
                        var thumb = $('img.thumb')[scope.focus];
                        show_viewer({
                            proxy_url: thumb.getAttribute('data-proxy-url'),
                        });
                        event.preventDefault();
                    }
                } else if (scope.showing_viewer === true) {
                    if (event.which === 38) { // up
                        event.preventDefault();
                    } else if (event.which === 40) { // down
                        event.preventDefault();
                    } else if (event.which === 27) { // escape
                        if (scope.showing_metadata === true) {
                            toggle_metadata();
                        } else if (scope.showing_copies === true) {
                            toggle_copies();
                        } else {
                            hide_viewer();
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
            }
        });
    };

    $.Images = $.Images || {};
    $.Images.load_date = load_date;
    $.Images.bind_keys = bind_keys;
});
