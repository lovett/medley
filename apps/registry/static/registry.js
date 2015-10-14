MEDLEY.registry = (function () {
    'use strict'

    function deleteRecord (e) {
        var trigger;

        e.preventDefault();

        trigger = jQuery(this)

        jQuery.ajax({
            type: 'DELETE',
            url: '/registry?uid=' + (parseInt(trigger.attr('data-uid'), 10) || 0)
        }).done(function (data) {
            window.location.href = window.location.pathname;
        });
    }

    return {
        init: function () {
            var $form, validationRules, validationSettings;
            $form = jQuery('#insert-form');

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
                        type: 'PUT',
                        dataType: 'json',
                        url: '/registry',
                        data: $('INPUT, TEXTAREA', this).serialize()
                    }).done(function (data) {
                        var href = window.location.pathname;
                        href += '?uid=' + data.uid;
                        window.location.href = href;
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

            jQuery('#records').on('click', 'A.delete', deleteRecord);
        }
    };
})();


jQuery(document).ready(MEDLEY.registry.init);
