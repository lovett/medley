MEDLEY.index = (function () {
    'use strict'
    return {
        init: function () {
            jQuery('MAIN A').focusAsYouType();
        }
    };
})();

jQuery(document).ready(MEDLEY.index.init);
