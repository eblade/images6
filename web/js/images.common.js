$(function() {

    $.wait = function(ms) {
        var defer = $.Deferred();
        setTimeout(function() { defer.resolve(); }, ms);
        return defer;
    };

    $.scroll_to = function(id, offset) {
        var
            element = $(id),
            offset = offset || 0;
        if (element.length) {
            $('html, body').animate({
                scrollTop: $(element).offset().top - offset,
            }, 300);
        }
    };

});
