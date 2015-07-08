MEDLEY.topics = (function () {
    'use strict';

    var childWindow;

    function visitLinks(links) {
        var link;

        link = [].shift.call(links);

        if (!childWindow) {
            childWindow = window.open(link.getAttribute('href'), 'topic');
        } else {
            childWindow.location.href = link.getAttribute('href');
        }

        link.className += ' strikeout';

        setTimeout(function () {
            if (links.length > 0) {
                visitLinks(links);
            } else if (childWindow) {
                childWindow.close();
            }
        }, Math.floor(Math.random() * 3000) + 3000);
    }

    return {
        init: function () {
            jQuery('BUTTON.primary').on('click', function () {
                visitLinks(jQuery('#topics A'));
            });
        }
    };
}());
jQuery(document).ready(MEDLEY.topics.init);
