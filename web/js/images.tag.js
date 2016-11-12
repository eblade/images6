$(function() {
    var load = function(params) {
        params = params || Object();
        var tag = params.tag || 'tag';
        var override = params.override || false;
        $.Images.Viewer.focus = 0;
        if (document.location.hash !== '#' + tag) {
            document.location.hash = '#' + tag;
        } else if (!override) {
            return;
        }
        $.ajax({
            url: 'tag?tag=' + tag,
            success: function(data) {
                tag = data.tag;
                $.Images.Viewer.tag = tag;
                $.Images.Viewer.index_hash = 'tags';
                $('#viewer_feed')
                    .html('');
                $('#tag_this')
                    .html(tag)
                    .click(function() { load_tag({'tag': tag}); });
                $.each(data.entries, function(index, entry) {
                    $('#viewer_feed')
                        .append('<img data-self-url="' + entry.self_url +
                                '" data-state="' + entry.state +
                                '" data-state-url="' + entry.state_url +
                                '" data-check-url="' + entry.check_url +
                                '" data-proxy-url="' + entry.proxy_url +
                                '" data-strip="' + $.Images.Viewer.create_strip(entry) +
                                '" class="thumb state_' + entry.state + '" id="thumb_' + index +
                                '" src="' + entry.thumb_url +
                                '" title="' + index + '"/>');
                    $('#thumb_' + index)
                        .click(function(event) {
                            var id = parseInt(this.title);
                            var thumb = $('img.thumb')[id]
                            $.Images.Viewer.update_focus({focus: id});
                            $.Images.Viewer.show_viewer({
                                proxy_url: thumb.getAttribute('data-proxy-url'),
                                strip: $.Images.Viewer.fix_strip(thumb.getAttribute('data-strip')),
                            });
                        });
                });
                $.Images.Viewer.update_focus({focus: 0});
                $.Images.Viewer.total_count = data.count;
            },
        });
    };

    $(document)
        .ready(function() {
            $.Images.Viewer.bind_keys();
            $(window)
                .hashchange(function() {
                    load({
                        tag: document.location.hash.substr(1),
                    });
                });
            load({
                tag: document.location.hash.substr(1),
                override: true,
            });
        });
});
