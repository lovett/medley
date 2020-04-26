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
        payload.set('replace', 1)

        const response = await fetch('/registry', {
            method: 'PUT',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            MEDLEY.setSuccessMessage('Query saved.');
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
        const query = e.target.value;
        const multilineQuery = query.split(',').reduce((accumulator, segment) => {
            return accumulator + '\n' + segment.trim();
        });
        document.getElementById('query').value = multilineQuery;
        document.getElementById('search').setAttribute('disabled', true);

        setTimeout(() => {
            document.getElementById('visitors-form').submit();
        }, 250);

    }

    /**
     * Blank the saved query dropdown if the query is edited.
     *
     * Also show or hide the date adjustment buttons if the query has
     * a date clause.
     */
    function resetQueryMenu(e) {
        document.getElementById('saved').value = '';

        const buttons = document.querySelectorAll('button[data-shortcut^="query-date"]');

        if (e.target.value.indexOf('date ') === -1) {
            buttons.forEach(node => node.hidden = true);
        } else {
            buttons.forEach(node => node.hidden = false);
        }
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

        const endpoint = '/registry';
        const label = prompt('Enter a label for this IP');
        const td = annotateIcon.closest('td');

        if (label.trim() === '') {
            const response = await fetch(endpoint, {
                method: 'DELETE',
                mode: 'same-origin',
            });

            if (response.ok) {
                td.querySelector('.annotations').innerHTML = '<p></p>';
            } else {
                MEDLEY.setErrorMessage('Unable to clear the annotation.');
            }

            return;
        }

        let payload = new FormData()
        payload.set('key', `ip:${annotateIcon.dataset.ip}`);
        payload.set('value', label.trim());
        payload.set('replace', true);

        const response = await fetch(endpoint, {
            method: 'PUT',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            td.querySelector('.annotations').innerHTML = `<p>${label}</p>`;
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
                resetQueryMenu
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
