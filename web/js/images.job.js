$(function() {
    var jobs = function (id, more_id) {
        $(more_id).hide();

        var update = function (force) {
            $.ajax({
                url: 'job?page_size=20',
                method: 'GET',
                success: function (data) {
                    if (data.stats.failed === 0) {
                        $(id).removeClass('error').html((data.stats.new + data.stats.acquired + data.stats.active) || 'OK');
                        if (data.stats.active > 0) {
                            $(id).addClass('active');
                        } else {
                            $(id).removeClass('active');
                        }
                    } else {
                        $(id).removeClass('active').addClass('error').html(data.stats.error);
                    }
                    if ($.Images.jobs.showing || force) {
                        $(more_id).html('');
                        $(more_id).html('<table id="job_table"><thead>' +
                                                         '<th></th>' +
                                                         '<th>method</th>' +
                                                         '<th>time</th>' +
                                                         '<th>entry</th>' +
                                                         '<th>comment</th>' +
                                                         '</thead><tbody></tbody></table>');

                        $.each(data.entries, function(index, entry) {
                            var comment = '';
                            if (entry.method === 'jpeg_import') {
                                if (entry.options.is_derivative) {
                                    comment = 'Attach ' + entry.options.folder + '/' + entry.options.source_path;
                                } else {
                                    comment = 'Import ' + entry.options.folder + '/' + entry.options.source_path;
                                }
                            } else if (entry.method === 'raw_import') {
                                comment = 'Import ' + entry.options.folder + '/' + entry.options.source_path;
                            } else if (entry.method === 'imageproxy') {
                                comment = 'Generate proxy';
                            } else if (entry.method === 'delete') {
                                comment = 'Delete variant ' + entry.options.variant.purpose + '/'
                                    + entry.options.variant.version;
                            }
                            $('#job_table tbody')
                                .append('<tr>' +
                                        '<td class="state ' + entry.state + '">' + entry.state.substr(0, 1) + '</td>' +
                                        '<td class="method">' + entry.method + '</td>' +
                                        '<td class="time">' + (entry.stopped - entry.started).toFixed(3) + '</td>' +
                                        '<td class="entry">' + (entry.options.entry_id || '-') + '</td>' +
                                        '<td class="comment">' + (entry.message || comment) + '</td>' +
                                        '</tr>');
                        });

                        $(more_id)
                            .append('<div class="info">' + 
                                    data.stats.total + ' jobs (' +
                                    data.stats.new + ' new, ' + 
                                    data.stats.acquired + ' acquired, ' +
                                    data.stats.active + ' active, ' +
                                    data.stats.held + ' held, ' +
                                    data.stats.done + ' done and ' +
                                    data.stats.failed + ' failed)</div>' +
                                    '<div class="job_action_buttons">' + 
                                    '<div class="job_action_button" ' +
                                    'id="delete_jobs_button">clear all</div></div>');

                        $('#delete_jobs_button')
                            .click(function() {
                                $.ajax({
                                    url: '/job',
                                    method: 'DELETE',
                                    success: function(data) {},
                                    error: function(data) {
                                        $(id).addClass('error').html('ERROR');
                                    },
                                });
                            });
                    }
                },
                error: function (data) {
                    $(id).addClass('error').html('ERROR');
                },
            });
        };

        update(true);
        //window.setInterval(update, 5000);

        $(id).click(function(e) {
            if ($.Images.jobs.showing) {
                $.Images.jobs.showing = false;
                $(more_id).fadeOut(300);
            } else {
                $.Images.jobs.showing = true;
                $(more_id).fadeIn(300);
            }
        });
    };

    $.Images = $.Images || {};
    $.Images.jobs = jobs;
    $.Images.jobs.showing = false;
});
