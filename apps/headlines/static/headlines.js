MEDLEY.headlines = (function () {
    'use strict';

    let childWindow = null;
    let links = [];
    let worker = null;

    function onClick(e) {
        if (e.target.nodeName !== 'BUTTON') {
            return;
        }

        const limit = parseInt(e.target.dataset.limit, 10);
        const offset = parseInt(e.target.dataset.offset, 10);

        childWindow = window.open('about:blank');
        worker.postMessage(`start:${limit}:${offset}`);
    }

    return {
        init: function () {
            links = Array.from(document.querySelectorAll('#headlines A.title'));

            worker = new Worker('/headlines/static/headlines-worker.js');

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
