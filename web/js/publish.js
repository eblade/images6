$(function() {
    var Publication = function(args) {
        var args = args || {};
        var me = {
            current_page: 0,
        };

        me.entry = {
            metadata: {
                '*Schema': 'Publication',
                title: args.title || 'untitled',
                author: args.author || null,
                comment: args.comment || null,
                publish_ts: args.publish_ts || null,
                pages: [],
            },
        };

        me.create_page = function(args) {
            var set_as_current = args.set_as_current || false;
            var page = Page(args);
            var new_length = me.entry.metadata.pages.push(page);
            if (set_as_current) {
                me.current_page = new_length - 1;
            }
            return page;
        };

        return me;
    };
    
    var Page = function(args) {
        var args = args || {};
        var me = {
            '*Schema': 'Page',
        };

        me.number = args.number === undefined ? 0 : args.number;
        me.show = args.show === undefined ? true : args.show;
        me.width = args.width === undefined ? 80 : args.width;
        me.height = args.height === undefined ? 50 : args.height;
        me.elements = args.elements === undefined ? [] : args.elements;

        me.create_element = function(args) {
            var element = Element(args);
            me.elements.push(element);
            return element;
        };

        return me;
    };

    var Element = function(args) {
        var args = args || {};
        var me = {
            '*Schema': 'Element',
        };

        me.type = args.type || 'image';
        me.src = args.src || null;
        me.content = args.content || null;
        me.entry_id = args.entry_id || null;

        return me;
    };

    $.Images = $.Images || {};
    $.Images.Publication = Publication;
    $.Images.Page = Page;
    $.Images.Element = Element;
});
