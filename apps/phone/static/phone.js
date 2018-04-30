MEDLEY.phone = (function () {
    'use strict';

    var endpoint = window.location.pathname;

    function showCalleridForm(e) {
        e.preventDefault();
        var value = jQuery('#callerid-display-value').text().trim();
        jQuery('#caller-id').removeClass('hidden');
        jQuery('#caller-id-display').addClass('hidden');
        jQuery('INPUT[name=cid_value]').val(value).focus().select();
    }

    function hideCalleridForm(e) {
        if (e) {
            e.preventDefault();
        }
        jQuery('#caller-id').addClass('hidden');
        jQuery('#caller-id-display').removeClass('hidden');
    }

    function updateCallerId(e) {
        e.preventDefault();

        var form, cidNumber, cidValue;

        form = jQuery(this);
        cidNumber = form.find('INPUT[name=cid_number]');
        cidValue = form.find('INPUT[name=cid_value]');

        jQuery.ajax({
            type: 'PUT',
            dataType: 'json',
            url: form.attr('action'),
            data: {
                'cid_number': cidNumber.val(),
                'cid_value': cidValue.val()
            }
        }).done(function (data, status, xhr) {
            jQuery('#callerid-display-value').text(cidValue.val());
            cidValue.val('');
            hideCalleridForm();
        }).fail(function (xhr) {
            form.find('.error.message').text(xhr.statusText).removeClass('hidden');
        });
    }

    function updateBlacklist(e) {
        e.preventDefault();

        var action, data, form, method, number, url;

        form = jQuery(this);
        number = form.find('INPUT[name=number]').val();
        action = form.find('INPUT[name=action]').val();

        if (action === 'add') {
            method = 'PUT';
            url = form.attr('action');
            data = {
                number: number
            };
        } else {
            method = 'DELETE';
            url = form.attr('action') + '?number=' + number;
            data = null;
        }

        jQuery.ajax({
            method: method,
            dataType: 'json',
            url: url,
            data: data
        }).done(function (data, status, xhr) {
            var forms;
            forms = form.parent().find('FORM');

            jQuery('#blacklist-date').text('today');
            forms.find('.error.message').text('').addClass('hidden');
            forms.toggleClass('hidden');

            if (action === 'add') {
                form.closest('.segment').addClass('inverted');
            } else {
                form.closest('.segment').removeClass('inverted');
            }

        }).fail(function (xhr) {
            form.find('.error.message').text(xhr.statusText).removeClass('hidden');
        });
    }

    return {
        init: function () {
            jQuery('.edit-callerid').on('click', showCalleridForm);
            jQuery('.reset-callerid').on('click', hideCalleridForm);
            jQuery('FORM.blacklist').on('submit', updateBlacklist);
            jQuery('#caller-id').on('submit', updateCallerId);
        }
    };
})();

jQuery(document).ready(MEDLEY.phone.init);
