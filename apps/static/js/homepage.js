MEDLEY.homepage = (function () {
    'use strict'

    return {
        init: function () {
            MEDLEY.focusAsYouType('.item');
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.homepage.init);
