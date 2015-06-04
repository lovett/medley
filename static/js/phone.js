MEDLEY.phone = (function () {
    'use strict';

    var endpoint;

    endpoint = window.location.pathname;

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

    function updateBlacklist(e) {
        e.preventDefault();

        var form, action, number;

        form = jQuery(this);

        action = form.find('INPUT[name=action]').val();
        number = form.find('INPUT[name=number]').val();

        jQuery.ajax({
            type: 'POST',
            dataType: 'json',
            url: form.attr('action'),
            data: {
                action: action,
                number: number
            }
        }).done(function (data, status, xhr) {
            var forms;
            forms = form.parent().find('FORM');

            if (xhr.status === 204) {
                jQuery('#blacklist-date').text('today');
                forms.removeClass('error');
                forms.find('.error.message').text('');
                forms.toggleClass('hidden');
            }

            if (action === 'add') {
                form.closest('.segment').addClass('inverted');
            } else {
                form.closest('.segment').removeClass('inverted');
            }

        }).fail(function (xhr) {
            form.find('.error.message').html(xhr.statusText);
            form.addClass('error');
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

            jQuery('FORM.blacklist').on('submit', updateBlacklist);
        }
    }
})();

jQuery(document).ready(MEDLEY.phone.init);
