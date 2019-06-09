$(function() {
    $('[data-include]').each(function() {
        var e = $(this);
        $.ajax({
            url: '/snippets/' + e.data('include'),
            method: 'GET',
            dataType: 'html',
            success: function(html) {
                console.log('snippet `' + e.data('include') + '` loaded');
                e.html(html);
                e.prop('aria-loaded', true);
            },
            error: function() {
                console.log('snippet `' + e.data('include') + '` hidden');
                e.hide();
            }
        });
    });
});