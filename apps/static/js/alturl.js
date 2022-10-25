MEDLEY.alturl = (function () {
    'use strict';

    async function saveFavorite(e) {
        e.preventDefault();
        const url = e.target.dataset.url;

        let payload = new FormData();
        payload.set('key', 'alturl:bookmark');
        payload.set('value', url.toLowerCase());
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

    function filterStories(e) {
        if (!e.target.dataset.filter) {
            return;
        }

        e.preventDefault();

        const datePart = (date) => date.toISOString().split('T')[0];

        let targetDate = '';

        if (e.target.dataset.filter === 'today') {
            targetDate = datePart(new Date());
        }

        let visibleCount = 0;
        document.querySelectorAll('#collection LI.headline').forEach((node) => {
            node.hidden = (targetDate && node.dataset.date !== targetDate);
            if (node.hidden === false) {
                visibleCount++;
            }
        });

        document.querySelectorAll('#main-toolbar .date-filter').forEach((node) => {
            node.classList.remove('active');
            if (node.dataset.filter === e.target.dataset.filter) {
                node.classList.add('active');
            }
        });

        console.log(visibleCount);
        document.getElementById('no-matches').hidden = (visibleCount > 0);

    }

    function jumpToAnchor(e) {
        if (e.target.classList.contains('jump')) {
            e.preventDefault();
            document.querySelector(e.target.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        }
    }

    return {
        init: function () {
            const saveLink = document.getElementById('add-record');
            if (saveLink) {
                saveLink.addEventListener('click', saveFavorite)
            }

            document.addEventListener('click', filterStories);

            document.addEventListener('click', jumpToAnchor);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.alturl.init);
