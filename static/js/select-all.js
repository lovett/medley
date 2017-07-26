MEDLEY.selectAll = (function () {
    'use strict';

    function selectAll(e) {
        var range, targetSelector, target;
        e.preventDefault();
        targetSelector = jQuery(e.target).attr('data-selection-target');
        target = jQuery(targetSelector);

        if (document.selection) {
            document.selection.empty();
            range = document.body.createTextRange();
            range.moveToElementText(target.get(0));
            range.select();
        } else if (window.getSelection) {
            window.getSelection().empty();
            range = document.createRange();
            range.selectNode(target.get(0));
            window.getSelection().addRange(range);
        }
    }

    return {
        init: function () {
            const links = jQuery('.select-all').on('click', selectAll);

            links.first('data-sellection-immediate=1').trigger('click');
        }
    };

}());

jQuery(document).ready(MEDLEY.selectAll.init);
