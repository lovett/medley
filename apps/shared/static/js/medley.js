var MEDLEY = (function () {
    'use strict';

    function shortcuts (e) {
        if (e.target.nodeName === 'INPUT' || e.target.nodeName === 'TEXTAREA') {
            return;
        }

        if (e.shiftKey && e.which === 72) { // H
            window.location.href = document.querySelector('a[rel=home]').getAttribute('href');
            return;
        }
    };

    function preSubmit(e) {
        const form = e.target;
        const fields = form.querySelectorAll('input, textarea');

        Array.from(fields).forEach((field) => {
            field.value = field.value.trim();
            console.log(field.value);
        });
    };

    return {
        setSuccessMessage: function (message) {
            const el = document.getElementById('app-message');
            el.removeAttribute('hidden');
            el.classList.remove('error')
            el.classList.add('success')
            el.innerHTML = `<p>${message}</p>`;
        },

        setErrorMessage: function (message) {
            const el = document.getElementById('app-message');
            el.removeAttribute('hidden');
            el.classList.remove('success')
            el.classList.add('error')
            el.innerHTML = `<p>${message}</p>`;
        },

        init: function () {
            document.addEventListener(
                'keydown',
                shortcuts
            );

            document.addEventListener(
                'submit',
                preSubmit
            );
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.init);
