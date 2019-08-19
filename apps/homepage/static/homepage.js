MEDLEY.homepage = (function () {
    'use strict'

    return {
        init: function () {
            MEDLEY.focusAsYouType('A.item');
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.homepage.init);
