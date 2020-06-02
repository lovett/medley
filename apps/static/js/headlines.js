MEDLEY.headlines = (function () {
    'use strict';

    let childWindow = null;
    let links = [];
    let worker = null;

    function onClick(e) {
        if (e.target.nodeName !== 'BUTTON') {
            return;
        }

        e.preventDefault();

        const start = parseInt(e.target.dataset.walkStart, 10);
        const stop = parseInt(e.target.dataset.walkStop, 10);

        childWindow = window.open('about:blank');
        worker.postMessage(`${start}:${stop}`);
    }

    return {
        init: function () {
            links = Array.from(document.querySelectorAll('#headlines A.title'));

            worker = new Worker('/static/js/headlines-worker.js');

            worker.addEventListener('message', function (e) {
                const fields = e.data.split(':');
                if (fields[0] === 'visit') {
                    const linkIndex = parseInt(fields[1], 10);
                    const link = links[linkIndex];

                    childWindow.location = link.dataset.searchHref;
                    link.classList.add('clicked');
                }

                if (fields[0] === 'finish') {
                    childWindow.close();
                }
            });

            document.addEventListener('click', onClick);
        }
    };
}());

window.addEventListener('DOMContentLoaded',  MEDLEY.headlines.init);
