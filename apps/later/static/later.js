MEDLEY.later = (function () {
    'use strict';

    var applyShortcut;

    applyShortcut = function (e) {
        var trigger = jQuery(e.target);
        var target = trigger.closest('.field').find('INPUT,TEXTAREA').first();

        if (trigger.hasClass('remove-querystring')) {
            target.val(target.val().replace(/\?[^#]+/, ''));
            target.focus();
        } else if (trigger.hasClass('remove-hash')) {
            target.val(target.val().replace(/#.*/, ''));
            target.focus();
        } else if (trigger.hasClass('reset')) {
            target.val(target.attr('data-original-value'));
        } else if (trigger.hasClass('trim-sentence-from-start')) {
            target.val(target.val().replace(/^(.*?\.) ([A-Z].*)/m, '$2'));
            target.focus();
        } else if (trigger.hasClass('trim-sentence-from-end')) {
            target.val(target.val().replace(/^(.*\.) ([A-Z].*)/m, '$1'));
            target.focus();
        } else if (trigger.hasClass('trim-all')) {
            target.val('').focus();
        }
    };

    return {
        init: function () {
            var $form, $successMessage, $errorMessage, validationRules, validationSettings;
            $form = jQuery('.ui.form');
            $successMessage = jQuery('.green.message', $form);
            $errorMessage = jQuery('.error.message', $form);


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
                        url: '/archive',
                        data: $('INPUT, TEXTAREA', this).serialize()
                    }).done(function (data) {
                        $successMessage.removeClass('hidden');
                        window.location.href = '/archive';
                    }).fail(function (data) {
                        console.log(data.responseText);
                        $form.addClass('error');
                        $successMessage.addClass('hidden');
                        $errorMessage.text(data);
                    });
                }
            };

            $form.form(validationRules, validationSettings);

            jQuery('.shortcuts').on('click', 'A', applyShortcut);
        }

    };
})();


jQuery(document).ready(MEDLEY.later.init);
