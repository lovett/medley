MEDLEY.later = (function () {
    'use strict';

    /**
     * Post the form to the bookmarks app.
     */
    async function submitBookmark(e) {
        e.preventDefault();

        const button = e.target.querySelector('BUTTON')
        button.setAttribute('disabled', true);
        button.innerText = button.dataset.progressLabel;

        let payload = new FormData()
        payload.set('title', document.getElementById('title').value.trim());
        payload.set('url', document.getElementById('url').value.trim());
        payload.set('tags', document.getElementById('tags').value.trim());
        payload.set('comments', document.getElementById('comments').value.trim());

        const response = await fetch(e.target.getAttribute('action'), {
            method: 'POST',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            MEDLEY.setSuccessMessage('Bookmark saved.');

        } else {
            MEDLEY.setErrorMessage('The bookmarks could not be saved.');
        }

        button.removeAttribute('disabled')
        button.innerText = button.dataset.defaultLabel;
    }

    /**
     * Auto populate tags based on the URL's domain.
     */
    function automaticTags() {
        const tags = document.getElementById('tags');
        const url = document.getElementById('url');

        let matches = /reddit.com\/(r\/(.*?))\//.exec(url.value);

        if (matches && tags.value.indexOf('r/') === -1) {
            tags.value += ' ' + matches[1];
        }
    }

    /**
     * Remove unwanted boilerplate from the comments field.
     */
    function cleanupComments() {
        const comments = document.getElementById('comments');
        if (comments.value.toLowerCase().indexOf('reddit: the front page') > -1) {
            comments.value = '';
        }
    }

    /**
     * Show or hide shortcuts if the related field has a value.
     */
    function toggleShortcuts(e) {
        const value = e.target.value.trim();
        const field = e.target.closest('.field');
        const shortcuts = field.querySelector('.shortcuts');

        if (value === '' && !shortcuts.hasAttribute('hidden')) {
            shortcuts.setAttribute('hidden', true);
        }

        if (value !== '' && shortcuts.hasAttribute('hidden')) {
            shortcuts.removeAttribute('hidden');
        }
    }

    function dispatchSubmit(e) {
        if (e.target.id === 'later-form') {
            submitBookmark(e);
            return;
        }
    }

    function dispatchInput(e) {
        if (['url', 'comments'].indexOf(e.target.id) > -1) {
            toggleShortcuts(e);
            return;
        }
    }

    return {
        init: function () {
            document.addEventListener('submit', dispatchSubmit);
            document.addEventListener('input', dispatchInput);
            automaticTags();
            cleanupComments();
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.later.init);
