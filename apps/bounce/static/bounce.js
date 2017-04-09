MEDLEY.bounce = (function () {
    function submitRecord (e) {
        var field, form, errorMessage;

        e.preventDefault();

        form = jQuery(e.target);

        field = jQuery('#source', form);

        if (jQuery.trim(field.val()) === '') {
            errorMessage = 'Please provide a value for the Source field.';
        }

        field = jQuery('#destination', form);

        if (jQuery.trim(field.val()) === '') {
            errorMessage = 'Please provide a value for the Destination field.';
        }

        if (errorMessage) {
            jQuery('.error.message').removeClass('hidden').text(errorMessage);
            jQuery('.success.messsage').addClass('hidden');
            return;
        }


        jQuery.ajax({
            type: 'PUT',
            dataType: 'json',
            url: '/bounce',
            data: $('INPUT', form).serialize()
        }).done(function (data) {
            var href = window.location.pathname;
            window.location.href = href;
        }).fail(function () {
            jQuery('.error.message').removeClass('hidden').text('Invalid values');
            jQuery('.success.message').addClass('hidden');
        });
    }

    return {
        init: function () {
            jQuery('#insert-form').on('submit', submitRecord);
        }
    };

})();

jQuery(document).ready(MEDLEY.bounce.init);
