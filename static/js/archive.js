MEDLEY.archive = (function () {
    'use strict';

    function deleteBookmark (e) {
        var form, trigger;
        e.preventDefault();
        trigger = jQuery(this);
        form = trigger.closest('FORM');
        jQuery.ajax({
            type: form.attr('method'),
            url: form.attr('action'),
            data: $('INPUT', form).serialize()
        }).done(function () {
            trigger.closest('.event').remove();
            if (jQuery('MAIN .event').length === 0) {
                jQuery('.nothing-message').removeClass('hidden');
                jQuery('MAIN H1').remove();
            }
        }).fail(function () {
            console.log('error');
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
