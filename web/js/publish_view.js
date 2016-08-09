$(function() {
    var scope = {};

    var draw_page = function(page) {
        $('#content').html('');

        scope.terminal = $.Terminal.Terminal({
            id: 'page',
            container: '#content',
            width: page.width,
            height: page.height,
            block_height: scope.font.height,
            block_width: scope.font.width,
        });

        $.each(page.elements, function(index, element) {
            draw_element(element);
        });
    };

    var draw_element = function(element) {
        if (element.type === 'text') {
            draw_text_element(element);
        }
    };

    var draw_text_element = function(element) {
        scope.terminal.buffer[0] = element.content;
        scope.terminal.render(scope.font);
    };

    $('#publication_new_button')
        .click(function () {
            scope.publication = $.Images.Publication();
            var page = scope.publication.create_page({ set_as_current: true });
            page.create_element({
                type: 'text',
                content: 'Johan testar',
            });
            draw_page(page);
        }); 

    $('#publication_json')
        .click(function () {
            alert(JSON.stringify(scope.publication, null, 2));
        });

    scope.font = $.Terminal.Font({
        path: '/graphics/c64',
        success: function(font) {
            $('#content').html('c64 font loaded.')
        },
    });

});

