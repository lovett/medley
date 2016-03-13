MEDLEY.visitors = (function () {
    'use strict';

    var calculateDelta, queryToMultiline, saveQuery, resetQueryMenu;

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
            var el, timestamp, delta, label, deltaString, units, result;

            el = jQuery(this);

            timestamp = parseFloat(el.attr('data-timestamp-unix'));

            delta = timestamp - referenceTimestamp;
            label = (delta < 0)? 'earlier':'later';
            delta = Math.abs(delta);

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
            el.closest('TR').find('.delta .value').html(result);
            el.closest('TR').find('.delta .label').html(label);
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

    function applySelectedDateToQuery(dateText) {
        var query;
        query = jQuery('#q').val();

        query = query.trim().replace(/date.*\d{4}-\d{2}-\d{2}/g, '');
        query = 'date ' + dateText + '\n' + query;
        jQuery('#q').val(query);
        jQuery('#submit').trigger('click');
    }

    return {
        init: function () {
            jQuery('#save').on('click', saveQuery);

            jQuery('#q').on('keyup', resetQueryMenu);

            jQuery('#saved').on('change', function (e) {
                var query, multiline;
                query = jQuery(this).val();
                multiline = queryToMultiline(query);
                jQuery('#q').val(multiline);
                jQuery('#submit').focus();
            });

            jQuery('#matches').on('click', 'A.calc-delta', calculateDelta);

            jQuery('#datepicker').datepicker({
                'dateFormat': 'yy-mm-dd',
                'onSelect': applySelectedDateToQuery
            })

        }
    };
})();

jQuery(document).ready(MEDLEY.visitors.init);
