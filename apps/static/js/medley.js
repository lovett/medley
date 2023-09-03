var MEDLEY = (function () {
    'use strict';

    function focusFromHash() {
        const focusId = window.location.hash.replace('#', '');
        if (!focusId) {
            return;
        }

        const candidates = document.getElementsByClassName('hash-focus-candidate');
        Array.from(candidates).forEach((candidate) => {
            if (candidate.dataset.hashFocusId === focusId) {
                candidate.focus();
            }
        });
    }

    function globalShortcuts (e) {
        if (e.target.nodeName === 'INPUT' || e.target.nodeName === 'TEXTAREA') {
            return;
        }

        if (e.key === 'A') {
            const tag = document.getElementById('add-record');
            if (tag) {
                tag.click();
            }
            return;
        }

        if (e.key === 'Escape') {
            const tags = document.getElementsByClassName('cancel');
            if (tags.length === 0) {
                return;
            }

            tags[0].click();
            return;
        }

        if (e.key === 'E') {
            const tag = document.getElementById('edit-record');
            if (tag) {
                tag.click();
            }
            return;
        }

        if (e.key === 'H') {
            const tag = document.querySelector('meta[name=medley-home]');
            window.location.href = tag.getAttribute('content');
            return;
        }

        if (e.key === 'S') {
            const tag = document.querySelector('meta[name=medley-startpage]');
            window.location.href = tag.getAttribute('content');
            return;
        }

        if (e.key === 'U') {
            const tag = document.querySelector('meta[name=medley-app-home]');
            window.location.href = tag.getAttribute('content');
            return;
        }

        if (!isNaN(parseInt(e.key, 10))) {
            const tag = document.querySelector(`a[data-numeric-shortcut="${e.key}"]`);
            if (tag) {
                window.location.href = tag.getAttribute('href');
            }
        }
    };

    function preSubmit(e) {
        const form = e.target;
        const fields = form.querySelectorAll('input, textarea');

        Array.from(fields).forEach((field) => {
            field.value = field.value.trim();
        });
    };

    function clearMessage(e) {
        if (e && e.target.id !== 'app-message-close') {
            return;
        }

        if (e) {
            e.preventDefault();
        }

        const el = document.getElementById('app-message');
        el.setAttribute('hidden', '');
        el.classList.remove('error')
        el.innerHTML = '';
    }

    return {
        reactivateForm: function (form) {
            const buttons = form.querySelectorAll('button');
            Array.from(buttons).forEach((button) => {
                button.disabled = false;
                if (button.dataset.default) {
                    button.innerText = button.dataset.default;
                }
            });
        },

        deactivateForm: function (form) {
            const buttons = form.querySelectorAll('button');
            Array.from(buttons).forEach((button) => {
                button.disabled = true;
                if (button.dataset.alt) {
                    button.innerText = button.dataset.alt;
                }
            });
        },

        setSuccessMessage: function (message) {
            const el = document.getElementById('app-message');
            const template = document.getElementById('app-message-template');
            el.innerHTML = template.innerHTML;
            el.removeAttribute('hidden');
            el.classList.remove('error')
            el.classList.add('success')
            el.querySelector('p').innerHTML = message;
        },

        clearMessage: clearMessage,

        setErrorMessage: function (message) {
            const el = document.getElementById('app-message');
            el.removeAttribute('hidden');
            el.classList.remove('success')
            el.classList.add('error')
            el.innerHTML = `<p>${message}</p>`;
        },

        init: function () {
            document.addEventListener('click', clearMessage);
            document.addEventListener(
                'keydown',
                globalShortcuts
            );

            document.addEventListener(
                'submit',
                preSubmit
            );

            focusFromHash()
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.init);
