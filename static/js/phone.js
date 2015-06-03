MEDLEY.phone = (function () {
    'use strict';

    function updateCallerId(e) {
        e.preventDefault();

        var form, cidNumber, cidValue;

        form = jQuery(this);
        cidNumber = form.find('INPUT[name=cid_number]');
        cidValue = form.find('INPUT[name=cid_value]');

        jQuery.ajax({
            type: 'POST',
            dataType: 'json',
            url: form.attr('action'),
            data: {
                'cid_number': cidNumber.val(),
                'cid_value': cidValue.val()
            }
        }).done(function (data, status, xhr) {
            if (xhr.status === 204) {
                jQuery('#callerid-display-value').text(cidValue.val());
                cidValue.val('');
                form.find('.panel-trigger:first').trigger('click');
            }
        }).fail(function (xhr) {
            form.addClass('error');
            form.find('.error.message').html(xhr.statusText);
        });
    }

    return {
        init: function () {
            jQuery('#caller-id').form({
                cid: {
                    identifier: 'cid_value',
                    rules: [
                        {
                            type   : 'empty',
                            prompt : 'Please enter a value'
                        }
                    ]
                }
            }, {
                inline: true,
                onSuccess: updateCallerId
            });
        }
    }
})();

jQuery(document).ready(MEDLEY.phone.init);
