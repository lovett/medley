MEDLEY.homepage = (function () {
    'use strict'

    return {
        init: function () {
            MEDLEY.focusAsYouType('.item a');
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.homepage.init);
