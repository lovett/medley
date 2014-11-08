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

    return {
        init: function () {
            jQuery('.toggle-trigger').on('click', toggle);
        }
    }
})();

jQuery(document).ready(MEDLEY.init);
