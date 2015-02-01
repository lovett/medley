MEDLEY.later = (function () {
    'use strict'

    return {
        init: function () {
            var $form, validationRules, validationSettings;
            $form = jQuery('.ui.form');

            validationRules = {
                url: {
                    identifier: 'url',
                    rules: [
                        {
                            type: 'empty',
                            prompt: 'Please provide a URL'
                        }
                    ]
                }
            };

            validationSettings = {
                'onSuccess': function () {
                    jQuery.ajax({
                        type: 'POST',
                        url: window.location.pathname,
                        data: $('INPUT, TEXTAREA', this).serialize()
                    }).done(function (data) {
                        var $successMessage = jQuery('.green.message', $form);
                        var $errorMessage = jQuery('.error.message', $form);
                        if (data === 'ok') {
                            jQuery('INPUT, TEXTAREA', $form).val('');
                            $successMessage.removeClass('hidden').fadeOut(5000);
                        } else {
                            $form.addClass('error');
                            $successMessage.addClass('hidden');
                            $errorMessage.text(data);
                        }
                    });
                }
            };

            $form.form(validationRules, validationSettings);
        },

        receiveMessage: function (e) {
            console.log(e);
        }
    };
})();


jQuery(document).ready(MEDLEY.later.init);
jQuery(window).on('message', MEDLEY.later.receiveMessage);
