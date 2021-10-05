MEDLEY.speak = (function () {
    'use strict';

    /**
     * Post the form to the speak app.
     */
    async function setDefaultVoice(e) {
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
            var rows = e.target.closest('table').getElementsByTagName('tr');
            Array.from(rows).forEach((row) => row.classList.remove('default'));
            e.target.closest('tr').classList.add('default');
        } else {
            MEDLEY.setErrorMessage('Unable to set the default voice.');
        }

        button.removeAttribute('disabled')
        button.innerText = button.dataset.defaultLabel;
    }

    /**
     * Post the form to the speak app.
     */
    async function testVoice(e) {
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

    function dispatchSubmit(e) {
        if (e.target.classList.contains('default-voice')) {
            setDefaultVoice(e);
            return;
        }

        if (e.target.classList.contains('voice-test')) {
            testVoice(e);
            return;
        }
    }

    return {
        init: function () {
            document.addEventListener('submit', dispatchSubmit);
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.speak.init);
