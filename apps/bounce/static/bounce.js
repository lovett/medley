MEDLEY.bounce = (function () {
    function deleteRecord (e) {
        var trigger;

        e.preventDefault();

        trigger = jQuery(e.target).closest('A');

        jQuery.ajax({
            type: 'DELETE',
            url: '/bounce?uid=' + (parseInt(trigger.attr('data-uid'), 10) || 0)
        }).done(function (data) {
            window.location.reload();
        });
    }

    function submitRecord (e) {
        var field, form, errorMessage;

        e.preventDefault();

        form = jQuery(e.target);

        field = jQuery('#site', form);

        if (jQuery.trim(field.val()) === '') {
            errorMessage = 'Please provide a value for the Site field.';
        }

        field = jQuery('#group', form);

        if (jQuery.trim(field.val()) === '') {
            errorMessage = 'Please provide a value for the Group field.';
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
            jQuery('#bounces').on('click', 'A.delete', deleteRecord);
        }
    };

})();

jQuery(document).ready(MEDLEY.bounce.init);
