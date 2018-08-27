MEDLEY.topics = (function () {
    'use strict';

    var childWindow, links, worker;

    function visitLink(index) {
        var target = links[index];

        childWindow.location = target.getAttribute('href');
        target.classList.add('strikeout');
    }

    return {
        init: function () {
            links = jQuery('#headlines A.search');

            worker = new Worker('/headlines/static/headlines-worker.js');

            worker.addEventListener('message', function (e) {
                var fields = e.data.split(':');
                if (fields[0] === 'visit') {
                    visitLink(parseInt(fields[1], 10));
                }

                if (fields[0] === 'finish') {
                    childWindow.close();
                }
            });

            jQuery('BUTTON').on('click', function () {
                var message = 'start'
                message += ':' + parseInt(jQuery(this).attr('data-limit'), 10);
                message += ':' + parseInt(jQuery(this).attr('data-offset'), 10);

                childWindow = window.open('about:blank');
                worker.postMessage(message);
            });
        }
    };
}());
jQuery(document).ready(MEDLEY.topics.init);
