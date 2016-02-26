MEDLEY.topics = (function () {
    'use strict';

    var childWindow;

    function visitLinks(links, counter) {
        var index;

        if (counter < links.length) {
            index = counter;
        } else {
            index = counter - links.length;
        }

        if (!childWindow) {
            childWindow = window.open(links[index].getAttribute('href'), 'topic');
        } else {
            childWindow.location.href = links[index].getAttribute('href');
        }

        links[index].className += ' strikeout';

        setTimeout(function () {
            if (counter < 30) {
                visitLinks(links, counter + 1);
            } else if (childWindow) {
                childWindow.close();
            }
        }, Math.floor(Math.random() * 3000) + 3000);
    }

    return {
        init: function () {
            jQuery('BUTTON').on('click', function () {
                visitLinks(jQuery('#topics A'), 0);
            });
        }
    };
}());
jQuery(document).ready(MEDLEY.topics.init);
