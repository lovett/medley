MEDLEY.visitors = (function () {
    'use strict';

    var queryToMultiline, saveQuery, applyShortcut;

    queryToMultiline = function (query) {
        return query.split(',').reduce(function (accumulator, segment) {
            return accumulator + '\n' + segment.trim();
        });
    };

    saveQuery = function (e) {
        e.preventDefault();
        var name = prompt("Provide a name for this query:");

        if (name === false) {
            return;
        }

        jQuery.ajax({
            type: 'POST',
            dataType: 'json',
            url: '/annotations',
            data: {
                'key': 'visitors:' + name.toLowerCase(),
                'value': jQuery('#q').val()
            }
        }).done(function (data) {
            var opt = jQuery('<option></option>');
            opt.attr('value', data.value);
            opt.text(data.key);
            jQuery('#saved').prepend(opt).val(data.value);
        });
    };

    applyShortcut = function (e) {
        var keyword, value, query, re;
        e.preventDefault();
        keyword = jQuery(this).attr('data-keyword');
        value = jQuery(this).attr('data-value');
        query = jQuery('#q').val();

        re = new RegExp('^' + keyword + ' .*\n');
        query = query.trim().replace(re, '');
        query = keyword + ' ' + value + '\n' + query;
        jQuery('#q').val(query);
        jQuery('#submit').trigger('click');
    };

    return {
        init: function () {
            jQuery('#save').on('click', saveQuery);
            jQuery('.shortcuts').on('click', 'A', applyShortcut);

            jQuery('#saved').on('change', function (e) {
                var query, multiline;
                query = jQuery(this).val();
                multiline = queryToMultiline(query);
                jQuery('#q').val(multiline);
                jQuery('#submit').focus();
            });

        }
    };
})();

jQuery(document).ready(MEDLEY.visitors.init);
