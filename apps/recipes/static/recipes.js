MEDLEY.recipes = (function () {
    function toggleStrike(e) {
        e.target.classList.toggle('done');
    }

    return {
        init: function () {
            document.addEventListener(
                'click',
                toggleStrike
            );
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.recipes.init);
