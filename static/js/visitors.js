MEDLEY.visitors = (function () {
    'use strict';

    var queryToMultiline, saveQuery, applyShortcut;

    queryToMultiline = function (query) {
        return query.split(',').reduce(function (accumulator, segment) {
            return accumulator + '\n' + segment.trim();
        });
    };

    saveQuery = function (e) {
        var activeName, name;

        e.preventDefault();
        activeName = jQuery('#saved OPTION:selected').text();
        if (activeName.indexOf(':') > -1) {
            activeName = activeName.split(':', 2).pop();
        }

        name = prompt("Provide a name for this query:", activeName);

        if (name === false) {
            return;
        }

        jQuery.ajax({
            type: 'POST',
            dataType: 'json',
            url: '/annotations',
            data: {
                'key': 'visitors:' + name.toLowerCase(),
                'value': jQuery('#q').val(),
                'replace': true
            }
        }).done(function (data) {
            var newOpt, opts;
            opts = jQuery('#saved OPTION').detach();
            opts = opts.filter(function () {
                return jQuery(this).text() !== data.key;
            });

            newOpt = jQuery('<option></option>');
            newOpt.attr('value', data.value);
            newOpt.text(data.key);

            opts = opts.add(newOpt);
            opts.sort(function (a, b) {
                return $(a).text() > $(b).text()? 1:-1;
            });
            jQuery('#saved').html(opts);
            newOpt.attr('selected', true);
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
