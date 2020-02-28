MEDLEY.alturl = (function () {
    'use strict';

    async function saveFavorite(e) {
        e.preventDefault();
        const url = e.target.dataset.url;

        let payload = new FormData();
        payload.set('key', 'alturl:bookmark');
        payload.set('value', url);
        payload.set('skip_redirect', true);

        const response = await fetch('/registry', {
            method: 'POST',
            mode: 'same-origin',
            body: payload
        })

        if (response.ok) {
            MEDLEY.setSuccessMessage('URL bookmarked');
            e.target.hidden = true;
        } else {
            MEDLEY.setErrorMessage('The URL could not be bookmarked');
        }
    }

    return {
        init: function () {
            const saveLink = document.getElementById('add-record');
            if (saveLink) {
                saveLink.addEventListener('click', saveFavorite)
            }
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.alturl.init);
