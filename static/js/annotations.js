MEDLEY.annotations = (function () {
    'use strict'

    var deleteAnnotation = function (e) {
        e.preventDefault();

        var trigger = jQuery(this)

        jQuery.ajax({
            type: 'DELETE',
            url: '/annotation/' + (parseInt(trigger.attr('data-id'), 10) || 0),
        }).done(function (data) {
            console.log(data);
            if (data === "ok") {
                trigger.closest('TR').remove();
            }
        });
    };

    return {
        init: function () {
            var $form, validationRules, validationSettings;
            $form = jQuery('.ui.form');

            validationRules = {
                'key': {
                    identifier: 'key',
                    rules: [
                        {
                            type: 'empty',
                            prompt: 'Please provide a key'
                        }
                    ]
                },
                'value': {
                    identifier: 'value',
                    rules: [
                        {
                            type: 'empty',
                            prompt: 'Please provide a value'
                        }
                    ]
                }
            };

            validationSettings = {
                'onSuccess': function () {
                    jQuery.ajax({
                        type: 'POST',
                        dataType: 'json',
                        url: '/annotations',
                        data: $('INPUT, TEXTAREA', this).serialize()
                    }).done(function (data) {
                        var $successMessage = jQuery('.green.message', $form);
                        var $errorMessage = jQuery('.error.message', $form);
                        var clone = jQuery('#annotations TBODY TR').first().clone();

                        jQuery('INPUT, TEXTAREA', $form).val('');
                        $successMessage.removeClass('hidden').fadeOut(5000);
                        clone.find('TD:nth-child(1)').text(data.key);
                        clone.find('TD:nth-child(2)').text(data.value);
                        clone.find('TD:nth-child(3)').text(data.created);
                        clone.find('A.delete').attr('data-id', data.id);
                        jQuery('#annotations TBODY').prepend(clone);
                    }).fail(function () {
                        var $successMessage = jQuery('.green.message', $form);
                        var $errorMessage = jQuery('.error.message', $form);
                        $form.addClass('error');
                        $successMessage.addClass('hidden');
                        $errorMessage.text('Invalid values');
                    });
                }
            };

            $form.form(validationRules, validationSettings);

            jQuery('#annotations').on('click', 'A.delete', deleteAnnotation);
        }
    };
})();


jQuery(document).ready(MEDLEY.annotations.init);
