MEDLEY.recipes = (function () {
    function toggleStrike(e) {
        if (e.target.nodeName === 'P' || e.target.nodeName === 'LI') {
            e.target.classList.toggle('done');
        }
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
