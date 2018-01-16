MEDLEY.copyToClipboard = (function () {
    'use strict';

    function copyValue(value, trigger) {
        jQuery('#copy-to-clipboard-surrogate').val(value).select();
        document.execCommand('copy');
        jQuery('#copy-to-clipboard-surrogate').blur().val('');

        var icon = jQuery('.icon-copy', trigger);
        var messageHolder = jQuery('.message-holder');
        icon.addClass('copied');
        messageHolder.text('Copied!').show();

        setTimeout(function () {
            icon.removeClass('copied');
        }, 500);

        setTimeout(function () {
            messageHolder.fadeOut();
        }, 1000);
    }

    function findValue(e) {
        e.preventDefault();
        var trigger, selector, value;

        trigger = jQuery(this);

        value = jQuery(this).data('copytarget');

        if (!value) {
            selector = jQuery(this).data('copyselector');
            value = jQuery(selector).text();
        }

        if (!value) {
            return;
        }

        copyValue(value, trigger);
    }

    return {
        init: function () {
            var surrogate = jQuery('<form style="position:absolute;top:-999em;left:-999em"><textarea id="copy-to-clipboard-surrogate"></textarea></form>');
            jQuery('body').append(surrogate);
            jQuery('.copy-to-clipboard').on('click', findValue);
        }
    };

}());

jQuery(document).ready(MEDLEY.copyToClipboard.init);
