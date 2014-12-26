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

    var shortcuts = function (e) {
        var href;

        // all shortcuts will use alt and shift
        if (e.altKey !== true || e.shiftKey !== true) {
            return;
        }

        if (e.which === 85) { // u
            href = jQuery('HEADER .home:first').attr('href');
            if (href) {
                window.location.href = href;
            }

            return;
        }

        //console.log(e.which);
    };

    return {
        init: function () {
            jQuery('.toggle-trigger').on('click', toggle);

            jQuery(document).on('keydown', shortcuts);
        }
    }
})();

jQuery(document).ready(MEDLEY.init);
