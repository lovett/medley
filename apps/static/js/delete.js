MEDLEY.delete = (function () {

    function hideClosest(source, selector) {
        const target = source.closest(selector);
        if (target) {
            const visibleCount = target.parentNode.querySelectorAll(selector + ':not([hidden])').length;
            target.setAttribute('hidden', true);

            if (visibleCount === 1) {
                target.parentNode.setAttribute('hidden', true);
            } else {
                target.parentNode.removeAttribute('hidden');
            }
        }
    }

    function deleteResource(e) {
        if (!e.target.classList.contains('delete')) {
            return;
        }

        e.preventDefault();

        const deleteUrl = e.target.dataset.deleteUrl;
        const deleteRedirect = e.target.dataset.deleteRedirect;
        const hideSelector = e.target.dataset.hideClosest;

        if (!deleteUrl) {
            return;
        }

        fetch(deleteUrl, {
            method: 'DELETE'
        }).then(res => {
            if (res.ok) {
                if (hideSelector) {
                    hideClosest(e.target, hideSelector);
                }
                if (deleteRedirect) {
                    window.location.assign(deleteRedirect);
                }
            }
        }).catch(err => {
            console.log(err);
            const resourceName = e.target.dataset.deleteResourceName;
            MEDLEY.setErrorMessage(`The ${resourceName} could not be deleted.`);
        });
    }

    return {
        init: function () {
            document.addEventListener('click', deleteResource);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.delete.init);
