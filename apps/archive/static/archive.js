MEDLEY.archive = (function () {
    'use strict';

    function deleteBookmark (e) {
        var form, group, trigger;
        e.preventDefault();
        trigger = jQuery(this);
        group = trigger.closest('.group');

        form = trigger.closest('FORM');
        jQuery.ajax({
            type: 'DELETE',
            url: '/archive?uid=' + (parseInt(trigger.attr('data-uid'), 10) || 0)
        }).done(function () {
            trigger.closest('.bookmark').remove();
            if (group.find('.bookmark').length === 0) {
                group.remove();
            }

            if (jQuery('.bookmark').length === 0) {
                jQuery('.nothing-message').removeClass('hidden');
            }
        }).fail(function (data) {
            console.log(data.responseText);
        });
    }

    return {
        init: function () {
            jQuery('MAIN').on('click', 'A.delete', deleteBookmark);
            jQuery('MAIN A.delete.hidden').removeClass('hidden');
        }
    };
})();

jQuery(document).ready(MEDLEY.archive.init);
