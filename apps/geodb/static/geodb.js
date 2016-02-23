MEDLEY.geodb = (function () {
    var triggerUpdate = function (e) {
        e.preventDefault();

        jQuery('#update').attr('disabled', 1);
        jQuery('#progress').removeClass('hidden');
        jQuery('.error.message').addClass('hidden');

        jQuery.ajax({
            type: 'POST',
            url: '/geodb'
        }).done(function (data) {
            jQuery('#progress').html('Update complete.');
        }).fail(function (xhr, status, error) {
            jQuery('#update').removeAttr('disabled');
            jQuery('#progress').addClass('hidden');
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
