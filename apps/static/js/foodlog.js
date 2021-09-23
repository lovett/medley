MEDLEY.foodlog = (function () {
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
            method: 'POST',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            MEDLEY.setSuccessMessage('Entry saved.');
        } else {
            MEDLEY.setErrorMessage('The entry could not be saved.');
        }

        button.removeAttribute('disabled')
        button.innerText = button.dataset.defaultLabel;
    }

    function dispatchSubmit(e) {
        if (e.target.id === 'foodlog-form') {
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

window.addEventListener('DOMContentLoaded',  MEDLEY.foodlog.init);
