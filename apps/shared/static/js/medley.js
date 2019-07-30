var MEDLEY = (function () {
    'use strict';

    var toggle = function (e) {
        e.preventDefault();
        var trigger = jQuery(this);
        var target = trigger.nextAll('.toggle-target');
        var label = trigger.find('SPAN');
        target.toggleClass('hidden');
        if (target.hasClass('hidden')) {
            trigger.addClass('collapsed');
            label.text('Show');
        } else {
            trigger.addClass('expanded');
            label.text('Hide');
        }
    };

    var togglePanel = function (e) {
        e.preventDefault();
        var trigger = jQuery(this);
        var panel = trigger.closest('.panel');
        panel.parent().find('.panel').toggleClass('hidden');
    }

    var resetForm = function (e) {
        e.preventDefault();
        var form = jQuery(this).closest('FORM');
        form[0].reset();
        form.removeClass('error');
    };

    var shortcuts = function (e) {
        if (e.target.nodeName === 'INPUT' || e.target.nodeName === 'TEXTAREA') {
            return;
        }

        if (e.shiftKey && e.which === 72) { // H
            window.location.href = jQuery('HEADER a[rel=home]').attr('href');
            return;
        }
    };

    function getMasterToggleForTable(table) {
        var toggleId;
        toggleId = jQuery(table).attr('id') + '-master-toggle';
        return jQuery('#' + toggleId);
    }

    function getTableForMasterToggle(toggle) {
        var tableId;
        tableId = jQuery(toggle).attr('id').replace('-master-toggle', '');
        return jQuery('#' + tableId);
    }

    return {
        setSuccessMessage: function (message) {
            const el = document.getElementById('app-message');
            el.removeAttribute('hidden');
            el.classList.remove('error')
            el.classList.add('success')
            el.innerHTML = `<p>${message}</p>`;
        },

        setErrorMessage: function (message) {
            el.removeAttribute('hidden');
            el.classList.remove('success')
            el.classList.add('error')
            el.innerHTML = `<p>${message}</p>`;
        },

        init: function () {

            jQuery('.toggle-trigger').on('click', toggle);
            jQuery('.panel-trigger').on('click', togglePanel);

            jQuery('.form-reset').on('click', resetForm);

            jQuery(document).on('keydown', shortcuts);

            jQuery('TR.expandable').on('expand collapse', function (e) {
                var prevRow, table, masterToggle;

                prevRow = jQuery(this).prev('TR');
                table = prevRow.closest('TABLE');

                masterToggle = getMasterToggleForTable(table);

                if (e.type === 'expand') {
                    jQuery(this).addClass('expanded');
                    prevRow.find('.toggle').trigger('expand');
                } else if (e.type === 'collapse') {
                    jQuery(this).removeClass('expanded');
                    prevRow.find('.toggle').trigger('collapse');
                }

                jQuery('.master-toggle').trigger(e.type);
            });

            jQuery('.toggle').on('expand collapse', function (e) {
                if (e.type === 'expand') {
                    jQuery('.label', this).text('less');
                    jQuery('.icon', this).removeClass('cubes').addClass('cube');
                } else if (e.type === 'collapse') {
                    jQuery('.label', this).text('more');
                    jQuery('.icon', this).removeClass('cube').addClass('cubes');
                }
            });

            jQuery('A.toggle-next-row').on('click', function (e) {
                var nextRow;
                e.preventDefault();

                nextRow = jQuery(this).closest('TR').next('TR.expandable');

                if (nextRow.hasClass('expanded')) {
                    nextRow.trigger('collapse');
                } else {
                    nextRow.trigger('expand');
                }
            });

            jQuery('.master-toggle').on('click expand collapse', function (e) {
                var label, table;
                e.preventDefault();

                label = jQuery('.label', this);
                table = getTableForMasterToggle(this);

                if (e.type === 'expand') {
                    label.text('collapse');
                }

                if (e.type === 'collapse') {
                    label.text('expand');
                }

                if (e.type === 'click') {
                    if (label.text() === 'expand') {
                        label.text('collapse');
                        jQuery('TR.expandable', table).trigger('expand');
                    } else {
                        label.text('expand');
                        jQuery('TR.expandable', table).trigger('collapse');
                        return;
                    }
                }
            });
        }
    }
})();

jQuery(document).ready(MEDLEY.init);
