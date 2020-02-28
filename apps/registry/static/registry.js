MEDLEY.registry = (function () {
    'use strict';

    return {
        init: function () {
            if (MEDLEY.focusAsYouType) {
                MEDLEY.focusAsYouType('#collection A');
            }
        }
    };
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.registry.init);
