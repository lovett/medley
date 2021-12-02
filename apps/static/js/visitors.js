MEDLEY.visitors = (function () {
    'use strict';

    /**
     * Store a query in the registry.
     */
    async function saveQuery (e) {
        e.preventDefault();

        const menu = document.getElementById('saved');
        const queryField = document.getElementById('query');

        const queryName = prompt("Name this query:");

        if (!queryName) {
            return;
        }

        let payload = new FormData()
        payload.set('key', `visitors:${queryName.toLowerCase()}`);
        payload.set('value', queryField.value);
        payload.set('skip_redirect', 1);

        const response = await fetch(e.target.href, {
            method: 'POST',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            MEDLEY.setSuccessMessage('Query saved.');
            setTimeout(submitQuery, 1000);
        } else {
            MEDLEY.setErrorMessage('The query could not be saved.');
        }
    };

    /**
     * Show or hide a table row containing the full log line.
     */
    function toggleNextRowVisibility(e) {
        if (e.target.classList.contains('toggle-next-row') === false) {
            return;
        }

        e.preventDefault();

        const nextRow = e.target.closest('TR').nextElementSibling;

        if (!nextRow) {
            return;
        }

        nextRow.classList.toggle('expanded');

        if (nextRow.classList.contains('expanded')) {
            e.target.innerText = e.target.dataset.expandedLabel;
            return;
        }

        e.target.innerText = e.target.dataset.defaultLabel;
    }

    /**
     * Present a saved query.
     */
    function displaySavedQuery(e) {
        document.getElementById('query').value = e.target.value.split(';').reduce((accumulator, segment) => {
            return accumulator + '\n' + segment.trim();
        });

        submitQuery();
    }

    /**
     * Send the current search query to the server.
     */
    function submitQuery() {
        setTimeout(() => {
            document.getElementById('visitors-form').submit();
        }, 250);
    }

    /**
     * Show or hide the date adjustment buttons if the query has
     * a date clause.
     */
    function adjustSearchOptions(e) {
        const buttons = document.querySelectorAll('button[data-shortcut^="query-date"]');
        const hidden = e.target.value.indexOf('date ') === -1;
        buttons.forEach(node => node.hidden = hidden);
    }

    /**
     * Associate an IP address with a label.
     */
    async function annotateIp(e) {
        const annotateIcon = e.target.closest('.annotate-ip')

        if (!annotateIcon) {
            return;
        }

        e.preventDefault();

        const tag = document.querySelector('meta[name=medley-registry]');
        const endpoint = tag.getAttribute('content');
        const container = annotateIcon.closest('td').querySelector('.annotations');
        const existingLabel = container.innerText;
        const label = prompt('Enter a label for this IP (leave empty to erase):', existingLabel);

        let payload = new FormData()
        payload.set('key', `ip:${annotateIcon.dataset.ip}`);
        payload.set('value', label.trim());
        payload.set('replace', true);

        const response = await fetch(endpoint, {
            method: 'POST',
            body: payload
        })

        if (response.ok) {
            container.innerHTML = `<p>${label}</p>`;
        } else {
            MEDLEY.setErrorMessage('The annotation not be saved.');
        }
    }

    return {
        init: function () {
            document.getElementById('add-record').addEventListener(
                'click',
                saveQuery
            );

            document.getElementById('saved').addEventListener(
                'change',
                displaySavedQuery
            );

            document.getElementById('query').addEventListener(
                'keyup',
                adjustSearchOptions
            );

            document.addEventListener(
                'click',
                annotateIp
            );

            document.addEventListener(
                'click',
                toggleNextRowVisibility
            );
        }
    }
}());

window.addEventListener('DOMContentLoaded',  MEDLEY.visitors.init);
