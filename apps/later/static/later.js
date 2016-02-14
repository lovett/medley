MEDLEY.later = (function () {
    'use strict';

    function submitForm(e) {
        var form, field, errorMessage;
        e.preventDefault();

        form = jQuery(this);

        field = jQuery('#url', form);

        if (jQuery.trim(field.val()) === '') {
            errorMessage = 'Please provide a URL';
        }

        if (errorMessage) {
            jQuery('.error.message').removeClass('hidden').text(errorMessage);
            jQuery('.success.messsage').addClass('hidden');
            return;
        }


        jQuery.ajax({
            type: form.attr('method'),
            url: form.attr('action'),
            data: $('INPUT, TEXTAREA', form).serialize()
        }).done(function (data) {
            jQuery('.error.message').addClass('hidden');
            jQuery('.success.message').removeClass('hidden');
            window.location.href = '/archive';
        }).fail(function (data) {
            jQuery('.error.message').removeClass('hidden').text(data.statusText);
            jQuery('.success.message').addClass('hidden');
            form.addClass('error');
        });
    }

    function automaticTags() {
        var url, tagsField, tags, matches;
        tagsField = $('#tags');
        tags = tagsField.val();
        url = $('#url').val();

        matches = /reddit.com\/(r\/(.*?))\//.exec(url);

        if (matches) {
            tags += ' ' + matches[1];
        }

        tagsField.val(tags);
    }

    function cleanupComments() {
        if ($('#comments').val().indexOf('reddit: the front page') > -1) {
            $('#comments').val('');
        }
    }

    function applyShortcut(e) {
        var trigger = jQuery(e.target);
        var target = trigger.closest('.field').find('INPUT,TEXTAREA').first();

        if (trigger.hasClass('remove-querystring')) {
            target.val(target.val().replace(/\?[^#]+/, ''));
            target.focus();
        } else if (trigger.hasClass('remove-hash')) {
            target.val(target.val().replace(/#.*/, ''));
            target.focus();
        } else if (trigger.hasClass('revert')) {
            target.val(target.attr('data-original-value'));
        } else if (trigger.hasClass('trim-sentence-from-start')) {
            target.val(target.val().replace(/^(.*?\.) ([A-Z].*)/m, '$2'));
            target.focus();
        } else if (trigger.hasClass('trim-sentence-from-end')) {
            target.val(target.val().replace(/^(.*\.) ([A-Z].*)/m, '$1'));
            target.focus();
        } else if (trigger.hasClass('trim-all')) {
            target.val('');
            target.focus();
        }
    }

    function toggleShortcuts(e) {
        var shortcuts, target, val;
        target = jQuery(this);
        shortcuts = target.closest('.field').find('.shortcuts A');
        val = jQuery.trim(target.val());
        if (val === '') {
            shortcuts.addClass('hidden');
        } else {
            shortcuts.removeClass('hidden');
        }
    }

    return {
        init: function () {
            jQuery('#later-form').on('submit', submitForm);

            jQuery('.shortcuts').on('click', 'A', applyShortcut);

            jQuery('#url, #comments').on('input', toggleShortcuts);

            toggleShortcuts.apply('#url');
            toggleShortcuts.apply('#comments');

            automaticTags();
            cleanupComments();
        }

    };
})();


jQuery(document).ready(MEDLEY.later.init);
