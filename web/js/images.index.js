$(function() {
    var
        menu_div = '#index_menu',
        feed_div = '#index_feed';

    var load_menu = function() {
        $.ajax({
            url: '/importer',
            success: function(data) {
                $.each(data.entries, function(index, trigger) {
                    $(menu_div)
                        .append('<div id="menu_trig_' + trigger.name +
                                '" class="index_menu_button">import from ' + trigger.name +
                                '</div>');
                    $('#menu_trig_' + trigger.name)
                        .click(function() {
                            $(menu_div).hide();
                            $.ajax({
                                url: trigger.trig_url,
                                method: 'POST',
                                success: function(data) {
                                    monitor('/importer/status', 'importing', 'scanning', 'importing',
                                        feed_div, function() {
                                            load_index(feed_div);
                                            $(feed_div).fadeIn(400)
                                            $(menu_div).fadeIn(400)
                                        }
                                    );
                                },
                                error: function(data) {
                                    alert('Error');
                                },
                            });
                        });
                });
                $(menu_div)
                    .append('<div id="menu_trig_purge" class="index_menu_button">purge</div>');
                $('#menu_trig_purge')
                    .click(function() {
                        $(menu_div).hide();
                        $.ajax({
                            url: '/purger/trig',
                            method: 'POST',
                            success: function(data) {
                                monitor('/purger/status', 'purging', 'reading', 'deleting',
                                    feed_div, function() {
                                        load_index(feed_div);
                                        $(feed_div).fadeIn(400)
                                        $(menu_div).fadeIn(400)
                                    }
                                );
                            },
                            error: function(data) {
                                alert('Error');
                            },
                        });
                    });
            },
        });
    };

    var monitor = function(url, caption, before, active, div, callback) {
        $(div)
            .html('<h2>' + caption + '</h2>')
            .append('<div class="common_progress_outer"><div id="progress"></div></div>')
            .append('<div class="common_error_message" id="menu_failure"></div>');

        var poll = function() {
            $.ajax({
                url: url,
                success: function(data) {
                    if (data.failed > 0) {
                        $('#menu_failure').html(data.failed + ' failed');
                    }
                    $('#progress').css('width', data.progress + '%');
                    if (data.status === 'acquired' || data.status === before || data.status === active) {
                        window.setTimeout(function() { poll(); }, 1000);
                    } else {
                        $(div).fadeOut(400)
                        $.wait(500).then(callback);
                    }
                },
                error: function(data) {
                },
            });
        };
        poll();
    };

    var load_index = function() {
        $(feed_div)
            .html('');
        $.ajax({
            url: '/date',
            success: function(data) {
                var
                    last_month = "",
                    this_month = "",
                    last_year = "",
                    this_year = "";

                $.each(data.entries, function(index, date) {
                    this_month = ("" + date.date).substring(0, 7);
                    this_year = ("" + date.date).substring(0, 4);
                    if (this_year !== last_year) {
                        last_month = '';
                        last_year = this_year;
                        $(feed_div).append('<div class="index_year">' + this_year + '</div>');
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
                        $(feed_div).append('<h2>' + month + '</h2>');
                    }
                    last_month = this_month;
                    var day = ("" + date.date).substring(8, 10);
                    var day_id = date.date;
                    var date_css = 'index_normal';
                    if (date.count === 0) {
                        date_css = 'index_empty';
                    } else if (date.count_per_state.pending > 0) {
                        date_css = 'index_pending';
                    } else if (date.count_per_state.purge > 0) {
                        date_css = 'index_purge';
                    }
                    if (date.short) {
                        $(feed_div)
                            .append('<div class="index_date_wrapper">' +
                                    '<div id="' + day_id +
                                        '" data-date="' + date.date +
                                        '" class="index_date_block ' + date_css + '">' + day + '</div>' +
                                    '<div class="index_date_short">' + date.short + '</div></div>');
                    } else {
                        $(feed_div)
                            .append('<div id="' + day_id +
                                    '" data-date="' + date.date +
                                    '" class="index_date_block ' + date_css + '">' + day + '</div>');
                    }
                    $(feed_div)
                        .find('#' + day_id)
                        .click(function() {
                            load_date(this.getAttribute('data-date'));
                        });
                    if (document.location.hash) {
                        scroll_to(document.location.hash);
                    }
                });
            },
            error: function(data) {
                $(feed_div).append('<div class="failure">Errors.</div>');
            },
        });
    };

    var load_date = function(date) {
        this.window.location = '/view/date#' + date;
    };

    var scroll_to = function(id) {
        var element = $(id);
        if (element.length) {
            $('html body').animate({
                scrollTop: $(element).offset().top,
            }, 500);
        }
    };

    load_menu('#index_menu');
    load_index('#index_feed');

    $(document)
        .ready(function() {
            $(window)
                .hashchange(function() {
                    if (document.location.hash) {
                        scroll_to(document.location.hash);
                    }
                });
        });
});
