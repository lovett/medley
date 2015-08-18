MEDLEY.visitors = (function () {
    'use strict';

    var calculateDelta, queryToMultiline, saveQuery, applyShortcut, resetQueryMenu;

    calculateDelta = function (e) {
        var referenceTimestamp, tbody, trigger;

        e.preventDefault();
        trigger = jQuery(this);
        tbody = trigger.closest('TBODY');
        referenceTimestamp = parseFloat(trigger.attr('data-timestamp-unix'));

        trigger.toggleClass('active');
        tbody.find('.calc-delta').not(trigger).removeClass('active');

        if (!trigger.hasClass('active')) {
            tbody.find('.delta .value').html(function () {
                return jQuery(this).closest('.delta').removeClass('hidden').attr('data-default');
            });
            return;
        } else {
            tbody.find('.delta').removeClass('hidden');
            trigger.parent().find('.delta').addClass('hidden');
        }

        function doubleDigitString(num) {
            if (num < 10) {
                return '0' + num.toString();
            } else {
                return num.toString();
            }
        }

        tbody.find('.calc-delta').html(function () {
            var el, timestamp, delta, deltaString, units, result;

            el = jQuery(this);

            timestamp = parseFloat(el.attr('data-timestamp-unix'));

            delta = Math.abs(timestamp - referenceTimestamp);

            units = [3600, 60, 1].reduce(function (acc, unit, index, arr) {
                var div;
                if (index === arr.length - 1) {
                    acc.push(delta);
                } else if (delta > unit) {
                    div = Math.floor(delta / unit);
                    delta -= unit * div;
                    acc.push(div);
                }
                return acc;
            }, []);

            units = units.map(doubleDigitString);

            if (units.length == 1) {
                result = '0:' + units[0];
            } else {
                result = units.join(':').replace(/^0/, '');
            }
            el.closest('TD').find('.delta .value').html(result);
        });
    };

    queryToMultiline = function (query) {
        return query.split(',').reduce(function (accumulator, segment) {
            return accumulator + '\n' + segment.trim();
        });
    };

    resetQueryMenu = function (e) {
        jQuery('#saved').val('');
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

            jQuery('#q').on('keyup', resetQueryMenu);

            jQuery('#saved').on('change', function (e) {
                var query, multiline;
                query = jQuery(this).val();
                multiline = queryToMultiline(query);
                jQuery('#q').val(multiline);
                jQuery('#submit').focus();
            });

            jQuery('#matches').on('click', 'A.calc-delta', calculateDelta);

        }
    };
})();

jQuery(document).ready(MEDLEY.visitors.init);
