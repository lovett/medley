MEDLEY.bounce = (function () {
    function submitRecord (e) {
        e.preventDefault();

        var form = jQuery(e.target);

        jQuery.ajax({
            type: 'PUT',
            dataType: 'json',
            url: '/bounce',
            data: $('INPUT', form).serialize()
        }).done(function (data, status, request) {
            var href = window.location.pathname + '?group=' + jQuery('#group').val();
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
