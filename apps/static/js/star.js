MEDLEY.star = (function () {

    function starResource(e) {
        if (!e.target.classList.contains('star')) {
            return;
        }

        const starUrl = e.target.dataset.starUrl;
        const starRedirect = e.target.dataset.starRedirect;

        if (!starUrl) {
            return;
        }

        fetch(starUrl, {
            method: 'PATCH'
        }).then(res => {
            if (res.ok) {
                if (starRedirect) {
                    window.location.assign(starRedirect);
                }
            }
        }).catch(err => {
            const resourceName = e.target.dataset.deleteResourceName;
            MEDLEY.setErrorMessage(`The ${resourceName} could not be starred.`);
        });
    }

    return {
        init: function () {
            document.addEventListener('click', starResource);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.star.init);
