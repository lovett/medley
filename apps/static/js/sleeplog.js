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

        console.log(payload);

        const response = await fetch(e.target.getAttribute('action'), {
            headers: {'Accept': 'application/json'},
            method: 'POST',
            mode: 'same-origin',
            body: payload
        })



        if (response.ok) {
            response.json().then((payload) => {
                history.replaceState(payload, '', `/sleeplog/${payload.uid}/edit`);
                MEDLEY.setSuccessMessage(`Entry #${payload.uid} ${payload.action}.`);
                document.getElementById('uid').setAttribute('value', payload.uid);
                document.getElementById('add-record').removeAttribute('hidden');

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
