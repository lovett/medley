MEDLEY.alturl = (function () {
    'use strict';

    async function saveFavorite(e) {
        e.preventDefault();
        const url = document.getElementById('url').value.trim();
        if (!url) {
            return;
        }

        let payload = new FormData();
        payload.set('key', 'alturl:bookmark');
        payload.set('value', url);

        const response = await fetch('/registry', {
            method: 'PUT',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            MEDLEY.setSuccessMessage('URL bookmarked');
        } else {
            MEDLEY.setErrorMessage('The URL could not be bookmarked');
        }
    }

    return {
        init: function () {
            const saveLink = document.getElementById('save-bookmark');
            if (saveLink) {
                saveLink.addEventListener('click', saveFavorite)
            }
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.alturl.init);
