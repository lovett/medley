MEDLEY.sleeplog = (function () {
    'use strict';

    /**
     * Post the entry input form.
     */
    async function submitEntry(e) {
        e.preventDefault();

        const button = e.target.querySelector('BUTTON')
        button.setAttribute('disabled', true);
        button.innerText = button.dataset.progressLabel;

        let payload = new FormData(e.target)

        const response = await fetch(e.target.getAttribute('action'), {
            headers: {'Accept': 'application/json'},
            method: 'POST',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            response.json().then((payload) => {
                window.location.href = payload.redirect;
            });
        } else {
            MEDLEY.setErrorMessage('The entry could not be saved.');
        }

        button.removeAttribute('disabled')
        button.innerText = button.dataset.defaultLabel;
    }

    function dispatchSubmit(e) {
        if (e.target.id === 'sleeplog-form') {
            submitEntry(e);
            return;
        }
    }

    return {
        init: function () {
            document.addEventListener('submit', dispatchSubmit);
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.sleeplog.init);
