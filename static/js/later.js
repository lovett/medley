MEDLEY.later = (function () {
    'use strict'

    var applyShortcut;

    applyShortcut = function (e) {
        var trigger = jQuery(e.target);
        var target = trigger.closest('.field').find('INPUT,TEXTAREA');
        if (trigger.hasClass('remove-querystring')) {
            target.val(target.val().replace(/\?[^#]+/, ''));
        } else if (trigger.hasClass('remove-hash')) {
            target.val(target.val().replace(/#.*/, ''));
        } else if (trigger.hasClass('reset')) {
            target.val(target.attr('data-original-value'));
        } else if (trigger.hasClass('trim-sentence-from-start')) {
            target.val(target.val().replace(/^(.*?\.) ([A-Z].*)/m, '$2'));
        } else if (trigger.hasClass('trim-sentence-from-end')) {
            target.val(target.val().replace(/^(.*\.) ([A-Z].*)/m, '$1'));
        }
    };

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
                            $successMessage.removeClass('hidden');
                            window.location.href = '/archive';
                        } else {
                            $form.addClass('error');
                            $successMessage.addClass('hidden');
                            $errorMessage.text(data);
                        }
                    });
                }
            };

            $form.form(validationRules, validationSettings);

            jQuery('.shortcuts').on('click', 'A', applyShortcut);
        }

    };
})();


jQuery(document).ready(MEDLEY.later.init);
