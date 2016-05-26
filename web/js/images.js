$(function() {
    var load_menu = function() {
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
                                    alert(data.result);
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
    };

    var monitor_import = function() {
        $.ajax({
            url: '/importer/status',
            success: function(data) {
                $('#menu_trig').html(data.status + ' (' + data.progress + '%)');
                if (data.failed > 0) {
                    $('menu_trig').append('<br/>' + data.failed + ' failed');
                }
                if (data.status === 'acquired' || data.status === 'scanning' || data.status === 'importing') {
                    window.setTimeout(monitor_import, 1000);
                }
            },
            error: function(data) {
            },
        });
    };

    load_menu();
});
