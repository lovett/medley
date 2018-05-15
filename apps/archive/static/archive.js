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
            url: '/archive?url=' + escape(trigger.attr('data-url'))
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

    function waybackAvailability (e) {
        var url;
        e.preventDefault();
        url = jQuery(this).data('url');

        jQuery
            .getJSON('?wayback=' + url)
            .done((data) => {
                if (!data.url) {
                    alert('Not available');
                    return;
                }
                window.location.href = data.url;
            })
    }

    return {
        init: function () {
            jQuery('MAIN').on('click', 'A.delete', deleteBookmark);
            jQuery('MAIN').on('click', 'A.wayback', waybackAvailability);
        }
    };
})();

jQuery(document).ready(MEDLEY.archive.init);
