MEDLEY.speak = (function () {
    'use strict';

    /**
     * Post the form to the speak app.
     */
    async function speakNow(e) {
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

        button.removeAttribute('disabled')
        button.innerText = button.dataset.defaultLabel;
    }

    return {
        init: function () {
            document.addEventListener('submit', speakNow);
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.speak.init);
