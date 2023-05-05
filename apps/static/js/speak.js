MEDLEY.speak = (function () {
    'use strict';

    /**
     * Post the form to the speak app.
     */
    async function speakNow(e) {
        if (e.target.id !== 'tryout') {
            return;
        }
        e.preventDefault();

        MEDLEY.deactivateForm(e.target);

        let payload = new FormData(e.target)

        if (payload.get('statement').length < 1) {
            MEDLEY.setErrorMessage('There was nothing to say.');
            MEDLEY.reactivateForm(e.target);
            return;
        }

        MEDLEY.clearMessage();

        const response = await fetch(e.target.getAttribute('action'), {
            method: 'POST',
            mode: 'same-origin',
            body: payload
        })

        setTimeout(() => MEDLEY.reactivateForm(e.target), 1000);
    }

    return {
        init: function () {
            document.addEventListener('submit', speakNow);
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.speak.init);
