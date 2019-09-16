$(function() {
    $('[data-include]').each(function(idx, element) {
        var $e = $(element), p = $e.data();
        $.ajax({
            url: '/snippets/' + p.include,
            method: 'GET',
            dataType: 'html',
            success: function(html) {
                $html = $(html);
                $html.data(p);
                if (p.replace) {
                    $e.replaceWith($html);
                } else {
                    $e.html($html);
                    $e.attr('aria-loaded', true);
                }
                $e.trigger('load');
                $html.trigger('load');
                console.log('snippet `' + p.include + '` loaded');
            },
            error: function() {
                $e.hide();
                console.log('snippet `' + p.include + '` hidden');
            }
        });
    });
});
