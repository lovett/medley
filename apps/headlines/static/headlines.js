MEDLEY.topics = (function () {
    'use strict';

    var childWindow, links, worker;

    function visitLink(index) {
        var link = links[index];

        if (link.classList.contains('strikeout')) {
            return;
        }

        if (!childWindow.closed) {
            childWindow.location.href = links[index].getAttribute('href');
            link.classList.add('strikeout');
        }
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
                var message = 'start:0:' + parseInt(jQuery(this).attr('data-count'), 10);
                childWindow = window.open('about:blank');
                worker.postMessage(message);
            });
        }
    };
}());
jQuery(document).ready(MEDLEY.topics.init);
