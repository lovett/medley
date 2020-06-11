MEDLEY.wayback = (function () {

    function check(e) {
        if (e.target.classList.contains('wayback') === false) {
            return;
        }

        e.preventDefault();

        e.target.innerText = 'checking...';

        fetch(e.target.dataset.url, {headers: {'Accept': 'application/json'}})
            .then(res => res.json())
            .then(data => {
                if (data.url) {
                    e.target.innerText = 'found!';
                    setTimeout(() => window.location.href = data.url, 500);
                    return;
                }

                this.label = 'not available';
            })
            .catch(error => {
                this.label = error.message;
            });
    }

    return {
        init: function () {
            document.addEventListener('click', check);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.wayback.init);
