MEDLEY.copyToClipboard = (function () {
    'use strict';

    function copy(e) {
        e.preventDefault();
        var copyTarget = jQuery(this).data('copytarget');
        if (!copyTarget) {
            return;
        }


        jQuery('#copy-to-clipboard-surrogate').val(copyTarget).select();
        document.execCommand('copy');
        jQuery('#copy-to-clipboard-surrogate').blur().val('');

        var icon = jQuery('.icon-copy', this);
        var messageHolder = jQuery('.message-holder');
        icon.addClass('copied');
        messageHolder.text('Copied!');

        setTimeout(function () {
            icon.removeClass('copied');
        }, 500);

        setTimeout(function () {
            messageHolder.fadeOut();
        }, 1000);
    }

    return {
        init: function () {
            var surrogate = jQuery('<form style="position:absolute;top:-999em;left:-999em"><input type="text" id="copy-to-clipboard-surrogate" value="" /></form>');
            jQuery('body').append(surrogate);
            jQuery('.copy-to-clipboard').on('click', copy);
        }
    };

}());

jQuery(document).ready(MEDLEY.copyToClipboard.init);
