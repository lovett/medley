MEDLEY.visitors = (function () {
    'use strict';

    var calculateDelta, queryToMultiline, saveQuery, resetQueryMenu, annotateIP;

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
        jQuery('.delete').addClass('hidden');
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
            type: 'PUT',
            dataType: 'json',
            url: '/registry',
            data: {
                'key': 'visitors:' + name.toLowerCase(),
                'value': jQuery('#query').val(),
                'replace': true
            }
        }).done(function () {
            jQuery('#submit').trigger('click');
        });
    };

    function applySelectedDateToQuery(dateText) {
        var query;
        query = jQuery('#query').val();

        query = query.trim().replace(/^\s*date.*\s*/g, '');
        query = 'date ' + dateText + '\n' + query;
        jQuery('#query').val(query);
        jQuery('#submit').trigger('click');
    }

    function deleteSavedQuery(e) {
        e.preventDefault();

        var selectedOption = jQuery('#saved OPTION:selected');

        console.log(selectedOption);

        jQuery.ajax({
            type: 'DELETE',
            url: '/registry/' + selectedOption.attr('data-id')
        }).done(function (data) {
            jQuery('#query').val('');
            jQuery('#submit').trigger('click');
        });
    }

    function annotateIP(e) {
        var existingValue, newValue, message, node;

        e.preventDefault();

        message = 'Enter a label for this IP';

        node = jQuery(e.target).closest('TD').find('.annotations P').first();

        if (node.length === 0) {
            node = jQuery('<p></p>');
            jQuery(e.target).closest('TD').find('.annotations').append(node);
        }

        existingValue = jQuery.trim(node.text());

        newValue = jQuery.trim(prompt('Enter a label for this IP', existingValue));

        if (newValue === '' || newValue === existingValue) {
            return;
        }

        jQuery.ajax({
            type: 'PUT',
            dataType: 'json',
            url: '/registry',
            data: {
                'key': 'ip:' + jQuery(this).attr('data-ip'),
                'value': newValue,
                'replace': true
            }
        }).done(function (data) {
            node.text(newValue);
        });
    }

    return {
        init: function () {
            jQuery('#save').on('click', saveQuery);

            jQuery('#query').on('keyup', resetQueryMenu);

            jQuery('.annotate-ip').on('click', annotateIP);

            jQuery('#saved').on('change', function (e) {
                var query, multiline;
                query = jQuery(this).val();
                multiline = queryToMultiline(query);
                jQuery('#query').val(multiline);
                jQuery('#submit').trigger('click');

                jQuery('.delete').removeClass('hidden');
            });

            jQuery('.delete').on('click', deleteSavedQuery);

            jQuery('#matches').on('click', 'A.calc-delta', calculateDelta);

            if (jQuery('#saved').val() !== '' && jQuery('#saved option:selected').text() !== 'default') {
                jQuery('.delete').removeClass('hidden');
            }


            jQuery('#datepicker').datepicker({
                'dateFormat': 'yy-mm-dd',
                'defaultDate': jQuery('META[name=active_date]').attr('content'),
                'onSelect': applySelectedDateToQuery,
                'showButtonPanel': true,
                'changeMonth': true,
                'changeYear': true,
                'maxDate': 0
            });

        }
    };
})();

jQuery(document).ready(MEDLEY.visitors.init);
