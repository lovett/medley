MEDLEY.visitors = (function () {
    'use strict';

    /**
     * Change the date keyword of the current query.
     */
    function adjustQueryDate(e) {
        const queryField = document.getElementById('query');
        const days = parseInt(e.target.value, 10);

        let dateString = 'today'

        if (days === -1) {
            dateString = 'yesterday'
        }

        if (days < -1) {
            const newDate = new Date(Date.now() + 86400000 * days);
            dateString = newDate.toISOString().replace(/T.*/, '')
        }

        let query = queryField.value.trim();

        query = query.replace(/^\s*date.*\s*/g, '');
        query = 'date ' + dateString + '\n' + query;
        queryField.value = query;
    }

    /**
     * Store a query in the registry.
     */
    async function saveQuery (e) {
        e.preventDefault();

        const menu = document.getElementById('saved');
        const queryField = document.getElementById('query');
        const submit = document.getElementById('submit');

        const queryName = prompt("Name this query:");

        if (!queryName) {
            console.log('nope');
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
     * Discard a previosly-saved query.
     */
    async function deleteSavedQuery(e) {
        e.preventDefault();

        const menu = document.getElementById('saved');
        const id = menu.selectedOptions[0].dataset.id;
        const endpoint = `/registry/?uid=${id}`;

        const response = await fetch(endpoint, {
            method: 'DELETE',
            mode: 'same-origin',
        });

        if (response.ok) {
            MEDLEY.setSuccessMessage('Query deleted.');
        } else {
            MEDLEY.setErrorMessage('The query could not be deleted.');
        }
    }

    /**
     * Show or hide the delete icon next to the saved queries dropdown.
     */
    function toggleQueryDelete(e) {
        console.log('ok');
        const menu = document.getElementById('saved');
        const deleteTrigger = document.getElementById('delete-saved-query');

        if (menu.value === '') {
            deleteTrigger.setAttribute('hidden', true)
        } else {
            deleteTrigger.removeAttribute('hidden');
        }
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
    }

    /**
     * Blank the saved query dropdown if the query is edited.
     */
    function resetQueryMenu(e) {
        document.getElementById('saved').value = '';
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

    function calculateDelta (e) {
        const trigger = e.target.closest('.calc-delta')

        if (!trigger) {
            return;
        }

        e.preventDefault();

        const tbody = e.target.closest('tbody');
        const referenceTimestamp = parseFloat(trigger.dataset.timestampUnix);

        trigger.classList.toggle('active');

        tbody.querySelectorAll('.calc-delta').forEach(el => {
            if (el !== trigger) {
                el.classList.remove('active')
            }
        });

        if (trigger.classList.contains('active') === false) {
            Array.from(tbody.querySelectorAll('.delta')).forEach(el => {
                el.removeAttribute('hidden');
                el.querySelector('.value').innerHTML = el.dataset.defaultDelta;
            });
            return;
        }

        Array.from(tbody.querySelectorAll('.delta')).forEach(el => {
            el.removeAttribute('hidden');
        });

        trigger.closest('td').querySelector('.delta').setAttribute('hidden', true);

        Array.from(tbody.querySelectorAll('.calc-delta')).forEach(el => {
            const timestamp = parseFloat(el.dataset.timestampUnix);

            let delta = timestamp - referenceTimestamp;
            const label = (delta < 0)? 'earlier' : 'later';
            delta = Math.abs(delta);

            let units = [3600, 60, 1].reduce((acc, unit, index, arr) => {
                var div;
                if (index === arr.length - 1) {
                    acc.push(delta);
                } else if (delta > unit) {
                    div = Math.floor(delta / unit);
                    delta -= unit * div;
                }
                return acc;
            }, []);

            units = units.map(val => String(val).padStart(2, '0'));

            let result = '';
            if (units.length == 1) {
                result = '0:' + units[0];
            } else {
                result = units.join(':').replace(/^0/, '');
            }

            el.closest('TD').querySelector('.delta .value').innerHTML = result;
            el.closest('TD').querySelector('.delta .label').innerHTML = label;
        });

    }

    return {
        init: function () {
            document.getElementById('date-slider').addEventListener(
                'input',
                adjustQueryDate
            );

            document.getElementById('save').addEventListener(
                'click',
                saveQuery
            );

            document.getElementById('delete-saved-query').addEventListener(
                'click',
                deleteSavedQuery
            );

            document.getElementById('saved').addEventListener(
                'change',
                toggleQueryDelete
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
                calculateDelta
            );
        }
    }
}());

window.addEventListener('DOMContentLoaded',  MEDLEY.visitors.init);
