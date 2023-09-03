MEDLEY.alturl = (function () {
    'use strict';

    const addId = 'add-bookmark';
    const removeId = 'remove-bookmark';

    async function removeBookmark(e) {
        if (e.target.id !== removeId) {
            return;
        }

        e.preventDefault();
        const id = e.target.dataset.bookmarkId;

        const response = await fetch(`/registry/${id}`, {
            method: 'DELETE',
            mode: 'same-origin'
        });

        if (response.ok) {
            MEDLEY.setSuccessMessage('Bookmark removed');
            e.target.hidden = true;
            document.getElementById(addId).hidden = false;
        } else {
            MEDLEY.setErrorMessage('The bookmark count not be removed');
        }
    }

    async function addBookmark(e) {
        if (e.target.id !== addId) {
            return;
        }

        e.preventDefault();
        const url = e.target.dataset.url;

        let payload = new FormData();
        payload.set('key', 'alturl:bookmark');
        payload.set('value', url.toLowerCase());
        payload.set('skip_redirect', true);
        payload.set('return_id', true);

        const response = await fetch('/registry', {
            method: 'POST',
            mode: 'same-origin',
            headers: {
                'Accept': 'application/json',
            },
            body: payload
        });

        if (response.ok) {
            MEDLEY.setSuccessMessage('Bookmark added');
            e.target.hidden = true;
            const json = await response.json();
            document.getElementById(addId).dataset.bookmarkId = json.rowid;

            document.getElementById(removeId).hidden = false;
        } else {
            MEDLEY.setErrorMessage('A bookmark could not be added');
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
            document.addEventListener('click', addBookmark);

            document.addEventListener('click', removeBookmark);

            document.addEventListener('click', filterStories);

            document.addEventListener('click', jumpToAnchor);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.alturl.init);
