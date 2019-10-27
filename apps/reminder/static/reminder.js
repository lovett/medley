MEDLEY.reminder = (function () {
    'use strict';

    const reminderForm  = document.getElementById('reminder-form');

    function onClick(e) {
        const template = e.target.closest('.template');
        if (!template) {
            return;
        }

        e.preventDefault();
        applyTemplate(template);
        reminderForm.submit();
    }

    function onSubmit(e) {

        const digitsRegex = /[^0-9]/g;
        const form = e.target;
        const minutes = document.getElementById('minutes').value.replace(digitsRegex, '');
        const hours = document.getElementById('hours').value.replace(digitsRegex, '');

        MEDLEY.deactivateForm(form);

        let timeframe = 0;
        if (minutes) {
            timeframe += parseInt(minutes, 10);
        }

        if (hours) {
            timeframe += parseInt(hours, 10) * 60;
        }

        if (timeframe == 0) {
            e.preventDefault();
            MEDLEY.setErrorMessage('The timeframe hasn\'t been set.');
            MEDLEY.reactivateForm(form)
            document.getElementById('minutes').focus();
            return;
        }

        const message = document.getElementById('message').value.trim();
        if (message === '') {
            e.preventDefault();
            MEDLEY.setErrorMessage('The message hasn\'t been set.');
            MEDLEY.reactivateForm(form)
            document.getElementById('message').focus();
            return;
        }

    }

    function applyTemplate(template) {
        const fields = ['message', 'comments', 'notification_id', 'url'];
        fields.forEach((field) => {
            document.getElementById(field).value = template.dataset[field] || '';

        });

        let minutes = parseInt(template.dataset.minutes, 10);
        let hours = 0;
        if (minutes > 59) {
            hours = Math.floor(minutes / 60);
            minutes %= 60;
        }

        document.getElementById('minutes').value = minutes;
        if (hours > 0) {
            document.getElementById('hours').value = hours;
        }
    }

    return {
        init: function () {
            document.addEventListener('click', onClick);
            document.getElementById('reminder-form');
            reminderForm.addEventListener('submit', onSubmit);
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.reminder.init);
