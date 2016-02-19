MEDLEY.registry = (function () {
    'use strict'

    function deleteRecord (e) {
        var trigger;

        e.preventDefault();

        trigger = jQuery(this)

        jQuery.ajax({
            type: 'DELETE',
            url: '/registry?uid=' + (parseInt(trigger.attr('data-uid'), 10) || 0)
        }).done(function (data) {
            window.location.href = window.location.pathname;
        });
    }

    function submitRecord (e) {
        var field, form, errorMessage;

        e.preventDefault();

        form = jQuery(this);

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
            href += '?uid=' + data.uid;
            window.location.href = href;
        }).fail(function () {
            jQuery('.error.message').removeClass('hidden').text('Invalid values');
            jQuery('.success.message').addClass('hidden');
        });
    }

    return {
        init: function () {
            jQuery('#insert-form').on('submit', submitRecord);
            jQuery('#records').on('click', 'A.delete', deleteRecord);
        }
    };
})();


jQuery(document).ready(MEDLEY.registry.init);
