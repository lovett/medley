MEDLEY.recipes = (function () {
    function toggleStrike(e) {
        if (e.target.closest('section') === null) {
            return;
        }

        if (e.target.nodeName === 'P' || e.target.nodeName === 'LI') {
            e.target.classList.toggle('done');
        }
    }

    return {
        init: function () {
            if (document.getElementById('recipe')) {
                document.addEventListener(
                    'click',
                    toggleStrike
                );
            }

            MEDLEY.focusAsYouType('#tagset A, #collection A');
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.recipes.init);
