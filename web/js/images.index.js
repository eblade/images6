$(function() {
    var
        menu_div = '#index_menu',
        sub_menu_div = '#index_sub_menu',
        feed_div = '#index_feed',
        jobs_div = '#index_menu_jobs';
        imports_div = '#index_menu_imports';

    var Menu = function(container_id) {
        var that = {};
        that.current = null;
        that.container_id = container_id;

        that.toggle = function(name, callback) {
            if (that.current === null || that.current !== name) {
                that.current = name;
                $(that.container_id).html('');
                callback();
                $(that.container_id).fadeIn(300);
            } else {
                $(that.container_id).fadeOut(300);
                that.current = null;
            }
        };

        that.showing = function(name) {
            return that.current === name;
        };

        that.close = function() {
            $(that.container_id).fadeOut(300);
            that.current = null;
        }

        return that;
    };

    var load_menu = function() {
        var menu = Menu(sub_menu_div);
        $(sub_menu_div).hide();

        $.Images.jobs(menu, jobs_div);
        $.Images.imports(menu, imports_div);

        $('#index_menu_tags')
            .click(function() {
                document.location.hash = 'tags';
            });

        $('#index_menu_dates')
            .click(function() {
                document.location.hash = 'dates';
            });

        $('#index_menu_purge')
            .click(function() {
                $(menu_div).hide();
                $.ajax({
                    url: 'purger/trig',
                    method: 'POST',
                    success: function(data) {
                        $.monitor('purger/status', 'purging', 'reading', 'deleting',
                            feed_div, function() {
                                load_dates(feed_div);
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
    };

    var load_dates = function(scroll_target) {
        $(feed_div)
            .html('');
        $.ajax({
            url: 'date?reverse=yes',
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
                    } else if (date.stats.pending > 0) {
                        date_css = 'index_pending';
                    } else if (date.stats.todo > 0 || date.stats.wip > 0) {
                        date_css = 'index_todo';
                    } else if (date.stats.purge > 0) {
                        date_css = 'index_purge';
                    }
                    if (date.short) {
                        $(feed_div)
                            .append('<div class="index_date_wrapper">' +
                                    '<div id="' + day_id +
                                        '" data-date="' + date.date +
                                        '" class="index_date_block ' + date_css + '">' + day + '</div>' +
                                    '<div class="index_date_short">' + date.stats.total + ' - ' + date.short + '</div></div>');
                    } else {
                        $(feed_div)
                            .append('<div class="index_date_wrapper">' +
                                    '<div id="' + day_id +
                                    '" data-date="' + date.date +
                                    '" class="index_date_block ' + date_css + '">' + day + '</div>' +
                                    '<div class="index_date_short">' + date.stats.total + '</div></div>');
                    }
                    $(feed_div)
                        .find('#' + day_id)
                        .click(function() {
                            load_date(this.getAttribute('data-date'));
                        });
                    //if (document.location.hash) {
                    //    $.scroll_to(document.location.hash, 200);
                    //}
                });
            },
            error: function(data) {
                $(feed_div).append('<div class="failure">Errors.</div>');
            },
        });
    };

    var load_date = function(date) {
        this.window.location = 'view-date#' + date;
    };

    var load_tags = function(tags) {
        $(feed_div).html('<div class="index_year">tags</div>');
        $.ajax({
            url: 'tag',
            method: 'GET',
            success: function(data) {
                $.each(data.entries, function(index, tag) {
                    $(feed_div)
                        .append('<div class="index_tag"><span class="index_tag_count">' +
                                tag.count + '</span><span class="index_tag">' +
                                tag.tag + '</span></div>');
                });
            },
            error: function(data) {
                $(feed_div).append('Error! Failed to fetch tags...');
            },
        });
    };

    load_menu('#index_menu');

    if (document.location.hash === '#tags') {
        load_tags();
    } else if (document.location.hash === '#dates') {
        load_dates();
    } else if (document.location.hash) {
        load_dates(document.location.hash);
    } else {
        document.location.hash = 'index';
    }

    $(document)
        .ready(function() {
            $(window)
                .hashchange(function() {
                    if (document.location.hash) {
                        if (document.location.hash === '#tags') {
                            load_tags();
                        } else if (document.location.hash === '#dates') {
                            load_dates();
                        } else {
                            $.scroll_to(document.location.hash, 200);
                        }
                    }
                });
        });
});
