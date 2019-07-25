MEDLEY.registry = (function () {
    'use strict';

    function submitRecord (e) {
        var field, form, errorMessage;

        e.preventDefault();

        form = jQuery(e.target);

        field = jQuery('#key', form);

        if (jQuery.trim(field.val()) === '') {
            errorMessage = 'Please provide a value for the Key field';
        }

        field = jQuery('#value', form);

        if (jQuery.trim(field.val()) === '') {
            errorMessage = 'Please provide a value for the Value field';
        }

        if (errorMessage) {
            jQuery('.error.message').removeClass('hidden').text(errorMessage);
            jQuery('.success.messsage').addClass('hidden');
            return;
        }

        jQuery.ajax({
            type: 'PUT',
            dataType: 'json',
            url: '/registry',
            data: $('INPUT, TEXTAREA', form).serialize()
        }).done(function (data) {
            var href = window.location.pathname;
            href += '?q=' + jQuery('#key').val();
            window.location.href = href;
        }).fail(function (data) {
            jQuery('.error.message').removeClass('hidden').text('Invalid values');
            jQuery('.success.message').addClass('hidden');
        });
    }

    return {
        init: function () {
            jQuery('#insert-form').on('submit', submitRecord);

            if ($().focusAsYouType) {
                jQuery('.glossary a').focusAsYouType();
            }
        }
    };
})();


jQuery(document).ready(MEDLEY.registry.init);
