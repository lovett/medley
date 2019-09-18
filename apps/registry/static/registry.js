MEDLEY.registry = (function () {
    'use strict';

    async function onInsertSubmit(e) {
        e.preventDefault();

        const keyField = document.getElementById('key');
        const endpoint = e.target.getAttribute('action');

        let payload = new FormData(e.target)

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

    return {
        init: function () {
            const insertForm = document.getElementById('insert-form');
            if (insertForm) {
                insertForm.addEventListener('submit', onInsertSubmit);
            }

            if (MEDLEY.focusAsYouType) {
                MEDLEY.focusAsYouType('.roots A');
            }
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.registry.init);
