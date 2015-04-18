MEDLEY.geodb = (function () {
    var triggerUpdate = function (e) {
        e.preventDefault();

        jQuery('#update').addClass('disabled');
        jQuery('#progress').addClass('active');

        jQuery.ajax({
            type: 'POST',
            dataType: 'json',
            url: '/geodb',
            data: {
                'action': 'update'
            }
        }).done(function (data) {
            window.location.reload();
        }).fail(function (xhr, status, error) {
            jQuery('#update').removeClass('disabled');
            jQuery('#progress').removeClass('active');
            jQuery('.error.message').removeClass('hidden');
        });
    };

    return {
        init: function () {
            jQuery('#update').on('click', triggerUpdate);
        }
    }
})();

jQuery(document).ready(MEDLEY.geodb.init);
