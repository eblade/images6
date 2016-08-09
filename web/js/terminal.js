$(function() {

    var TerminalFont = function(params) {
        var path = params.path;
        var success = params.success;
        var me = {
            image: new Image(),
            ready: false,
            image_ready: false,
            data_ready: false,
        };
        me.image.addEventListener("load", function () { 
            me.image_ready = true;
            me.ready = me.data_ready && me.image_ready;
            if (me.ready && success) { success(me); };
        });
        me.image.src = path + '.png';

        $.ajax({
            url: path + '.json',
            success: function(data) {
                me.map = data.map;
                me.name = data.name;
                me.background = data.background;
                me.foreground = data.foreground;
                me.width = data.width;
                me.height = data.height;
                me.data_ready = true;
                me.ready = me.data_ready && me.image_ready;
                if (me.ready && success) { success(me); };
            },
        });

        me.render = function (context, character, x, y, scale) {
            if (!me.ready) {
                return;
            }
            
            map = me.map[character];
            if (!map) {
                return;
            }

            context.drawImage(
                me.image,
                map.x * me.width,
                map.y * me.height,
                me.width,
                me.height,
                x * me.width * scale,
                y * me.height * scale,
                me.width * scale,
                me.height * scale
            );
        };

        return me;
    };

    var Terminal = function (args) {
        var me = {};
        me.width = args.width || 80;
        me.height = args.height || 50;
        me.x = args.x || 0;
        me.y = args.y || 0;
        me.block_width = args.block_height || 16;
        me.block_height = args.block_width || 16;
        me.scale = args.scale || 1;
        me.buffer = Array();
        me.id = args.id || 'canvas';
        me.container = args.container || '#content';

        $(me.container).append('<canvas class="terminal" id="' + me.id + '"></canvas>');
        me.canvas = document.getElementById(me.id)
        me.canvas.width = me.width * me.block_width * me.scale;
        me.canvas.height = me.height * me.block_width * me.scale;
        me.context = me.canvas.getContext("2d");
        me.canvas.addEventListener("mousedown", me.on_mouse_down, false);
        me.canvas.addEventListener("mousemove", me.on_mouse_move, false);

        me.clear = function () {
            me.context.clearRect(0, 0, me.canvas.width, me.canvas.height);
        };

        me.reset = function () {
            me.clear();
            me.buffer = Array();
        };

        me.render = function (font) {
            var
                buffer_height = me.buffer.length,
                start_y = 0,
                stop_y = Math.min(me.height, buffer_height)
            ;
            me.clear();
            me.draw_border();
            for (var y = start_y; y < stop_y; y++) {
                line = me.buffer[y];
                for (var x = 0, len = Math.min(line.length, me.width); x < len; x++) {
                    me.draw_character(font, line[x], x, y - start_y);
                }
            }
            //me.draw_links();
        };

        me.draw_character = function (font, character, x, y, scale) {
            font.render(me.context, character, x, y, scale || me.scale);
        };

        me.draw_links = function () {
            var
                links = me.buffer.links || Array(),
                link = null;

            for (var i = 0, len = links.length; i < len; i++) {
                link = links[i];
                me.draw_link(link);
            }
        };

        me.draw_link = function (link) {
            me.context.strokeRect(
                link.x1 * me.block_width,
                link.y1 * me.block_height,
                (link.x2 - link.x1) * me.block_width,
                (link.y2 - link.y1) * me.block_height
            )
        };

        me.draw_border = function () {
            me.context.fillStyle = '#4130a4';
            me.context.fillRect(0, 0, me.canvas.width, me.canvas.height);
        }

        me.get_link = function (x, y) {
            var
                links = me.buffer.links || Array(),
                link = null;

            for (var i = 0, len = links.length; i < len; i++) {
                link = links[i];
                if (x >= link.x1 * me.block_width 
                 && x <= link.x2 * me.block_width
                 && y >= link.y1 * me.block_height
                 && y <= link.y2 * me.block_height) {
                    
                    return link;
                }
            }
        };

        me.on_mouse_down = function (event) {
            var
                coords = me.canvas.relMouseCoords(event),
                link = me.get_link(coords.x, coords.y);

            if (link) {
                document.location = link.url;
            }
        };

        me.on_mouse_move = function (event) {
            var
                coords = me.canvas.relMouseCoords(event),
                link = me.get_link(coords.x, coords.y);

            if (link) {
                document.status = link.url;
                me.canvas.style.cursor = 'pointer';
            } else {
                me.canvas.style.cursor = 'auto';
            }
        };

        return me;
    };

    var parse = function (lines) {
        var state = 0,
            title,
            url,
            start,
            links = Array(),
            result_line;
            result = Array();

        for (var y = 0, len = lines.length; y < len; y++) {
            var 
                line = lines[y],
                result_x = 0;

            result_line = '';
            state = 0;
            for (var x = 0, llen = line.length; x < llen; x++) {
                c = line[x];
                if (state === 0  && c === '[') {
                    state = 1;
                    start = result_x;
                    title = '';
                    url = '';
                } else if (state === 0) {
                    result_line += c;
                    result_x++;
                } else if (state === 1  && c === '[') {
                    state = 2;
                } else if (state === 1) {
                    state = 0;
                } else if (state === 2 && c === '|') {
                    state = 3;
                } else if (state === 2) {
                    title += c;
                } else if (state === 3 && c === ']') {
                    state = 4;
                } else if (state === 3) {
                    url += c;
                } else if (state === 4 && c === ']') {
                    var link = {
                        x1: start,
                        x2: start + title.length + 2,
                        y1: y,
                        y2: y + 1,
                        title: title,
                        url: url,
                    };
                    links.push(link);
                    result_line += '[' + title + ']';
                    result_x += title.length + 2;
                    state = 0;
                }
            }
            result.push(result_line);
        }

        result.links = links;
        return result;
    };
    
    rel_mouse_coords = function (event){
        var totalOffsetX = 0;
        var totalOffsetY = 0;
        var canvasX = 0;
        var canvasY = 0;
        var currentElement = this;

        do {
            totalOffsetX += currentElement.offsetLeft
                          - currentElement.scrollLeft;
            totalOffsetY += currentElement.offsetTop
                          - currentElement.scrollTop;
        } while (currentElement = currentElement.offsetParent)

        canvasX = event.pageX - totalOffsetX;
        canvasY = event.pageY - totalOffsetY;

        return { x: canvasX, y: canvasY }
    };

    HTMLCanvasElement.prototype.relMouseCoords = rel_mouse_coords;

    $.Terminal = {
        Terminal: Terminal,
        Font: TerminalFont,
    };
});



