MEDLEY.index = (function () {
    'use strict'
    return {
        init: function () {
            jQuery('A.item').focusAsYouType();
        }
    };
})();

jQuery(document).ready(MEDLEY.index.init);
