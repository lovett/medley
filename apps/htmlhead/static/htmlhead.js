MEDLEY.htmlhead = (function () {
    'use strict';

    function filter(e) {
        e.preventDefault();
        const input = e.target.getElementsByTagName('input')[0];

        const rows = document.getElementById('tags').getElementsByTagName('TR');

        const wantedTag = input.value.toLowerCase();
        Array.from(rows).forEach((row) => {
            if (row.dataset.tagName.toLowerCase() === wantedTag) {
                row.removeAttribute('hidden');
            } else {
                row.setAttribute('hidden', true);
            }
        });
    }

    function reset(e) {
        const rows = document.getElementById('tags').getElementsByTagName('TR');
        Array.from(rows).forEach(row => row.removeAttribute('hidden'));
     }

    return {
        init: function () {
            document.getElementById('filter').addEventListener('submit', filter);
            document.querySelector('.secondary INPUT[type=reset]').addEventListener('click', reset);
        }
    }
}());

window.addEventListener('DOMContentLoaded',  MEDLEY.htmlhead.init);
