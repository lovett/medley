MEDLEY.delete = (function () {
    function deleteResource(e) {
        if (!e.target.classList.contains('delete')) {
            return;
        }

        const deleteUrl = e.target.dataset.deleteUrl;
        const deleteRedirect = e.target.dataset.deleteRedirect;
        if (!deleteUrl) {
            return;
        }

        fetch(deleteUrl, {
            method: 'DELETE'
        }).then(res => {
            if (res.ok) {
                if (deleteRedirect) {
                    window.location.assign(deleteRedirect);
                }
            }
        }).catch(err => {
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
