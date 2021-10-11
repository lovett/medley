MEDLEY.star = (function () {

    function toggle(e) {
        if (!e.target.classList.contains('star')) {
            return;
        }

        const endpoint = e.target.dataset.resourceUrl;

        if (!endpoint) {
            return;
        }

        let payload = new FormData();
        payload.set('toggle', 'star');

        fetch(endpoint, {
            method: 'PATCH',
            mode: 'same-origin',
            body: payload
        }).then(res => {
            if (res.ok) {
                window.location.assign(endpoint);
                return;
            }

            throw new Error();
        }).catch(err => {
            const resourceName = e.target.dataset.resourceName;
            MEDLEY.setErrorMessage(`The ${resourceName} could not be starred.`);
        });
    }

    return {
        init: function () {
            document.addEventListener('click', toggle);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.star.init);
