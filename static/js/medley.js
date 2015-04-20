var MEDLEY = (function () {
    'use strict';

    var toggle = function (e) {
        e.preventDefault();
        console.log('hi');
        var trigger = jQuery(this);
        console.log(trigger);
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

    var shortcuts = function (e) {
        var href;

        if (e.target.nodeName === 'INPUT' || e.target.nodeName === 'TEXTAREA') {
            return;
        }

        if (e.shiftKey && e.which === 191) { // ?
            jQuery('#shortcuts').modal('show');
            return;
        }

        if (e.shiftKey && e.which === 72) { // H
            href = jQuery('HEADER .home:first').attr('href');
            if (href) {
                window.location.href = href;
            }
            return;
        }
    };

    var selectAll = function (e) {
        var range;
        e.preventDefault();
        var target = jQuery(jQuery(this).attr('data-selection-target'));
        if (document.selection) {
            range = document.body.createTextRange();
            range.moveToElementText(target.get(0));
            range.select();
        } else if (window.getSelection) {
            range = document.createRange();
            range.selectNode(target.get(0));
            window.getSelection().addRange(range);
        }
    };

    return {
        init: function () {
            jQuery('.toggle-trigger').on('click', toggle);

            jQuery(document).on('keydown', shortcuts);

            jQuery('.select-all').on('click', selectAll);

            if (jQuery('#result').html() !== '') {
                jQuery('#result').prevAll('.select-all').trigger('click');
            }

            jQuery('.ui.radio.checkbox').checkbox();

            jQuery('A.row-toggle').on('click', function (e) {
                var label;
                e.preventDefault();
                label = jQuery('.label', this);

                label.text(label.text() === 'more' ? 'less':'more');
                jQuery('.icon', this).toggleClass('cube cubes');
                jQuery(this).closest('TR').next('TR.expandable').toggleClass('expanded');
            });
        }
    }
})();

jQuery(document).ready(MEDLEY.init);
