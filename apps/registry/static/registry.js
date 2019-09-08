MEDLEY.registry = (function () {
    'use strict';

    async function onInsertSubmit(e) {
        e.preventDefault();

        const keyField = document.getElementById('key');
        const valueField = document.getElementById('value');
        const endpoint = e.target.getAttribute('action');

        let payload = new FormData()
        payload.set('key', keyField.value);
        payload.set('value', valueField.value);

        const response = await fetch(endpoint, {
            method: 'PUT',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            let href = window.location.pathname;
            href += '?q=' + keyField.value + '*';
            window.location.href = href;
        } else {
            MEDLEY.setErrorMessage('The entry could not be saved.');
        }
    }

    function onSearchSubmit(e) {
        const queryField = document.getElementById('q');
        queryField.value = queryField.value.trim();
    }

    return {
        init: function () {
            const insertForm = document.getElementById('insert-form');
            if (insertForm) {
                insertForm.addEventListener(
                    'submit',
                    onInsertRecord
                );
            }

            const searchForm = document.getElementById('search-form');
            if (searchForm) {
                searchForm.addEventListener(
                    'submit',
                    onSearchSubmit
                )
            }

            if (MEDLEY.focusAsYouType) {
                MEDLEY.focusAsYouType('.roots A');
            }
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.registry.init);
