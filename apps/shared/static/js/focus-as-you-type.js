(function ($) {
    'use strict';
    $.fn.focusAsYouType = function(options) {
        var buffer, bufferDisplay, candidates, elements, settings;
        buffer = '';
        settings = $.extend({
            bufferLength: 10,
            candidateClass: 'focus-candidate',
            bufferDisplaySelector: '.focus-buffer-display'
        }, options);

        bufferDisplay = jQuery(settings.bufferDisplaySelector);

        elements = jQuery(this);

        candidates = elements.map(function (index, el) {
            var text = $(el).text().trim();

            text = text.split('\n').shift().toLowerCase();
            return text;
        }).get();

        function clearBuffer() {
            buffer = '';
            elements.removeClass(settings.candidateClass).blur();
            displayBuffer();
        }

        function displayBuffer() {
            bufferDisplay.text(buffer);
        }

        function match() {
            var matches, now, score;

            if (buffer === '') {
                clearBuffer();
                return;
            }

            displayBuffer();

            matches = candidates.map(function (candidate) {
                return (candidate.indexOf(buffer) === 0)? 1 : 0;
            });

            score = matches.reduce(function (accumulator, value) {
                return accumulator + value;
            });

            elements.removeClass(settings.candidateClass);

            if (score == 1) {
                $(elements[matches.indexOf(1)]).focus();
            } else {
                matches.forEach(function (match, index) {
                    if (match === 1) {
                        $(elements[index]).addClass(settings.candidateClass);
                    }
                });
            }
        }

        // Chrome won't send keypress events for non-printable
        // keys. Handle them on keyup instead.
        $(document).on('keyup', function (e) {
            if (e.which === 27) { // escape key
                clearBuffer();
                return;
            }

            if (e.which === 8 || e.which === 46) { // backspace, delete
                buffer = buffer.slice(0, buffer.length - 1);
                match();
            }
        });

        $(document).on('keypress', function (e) {
            // Backspace, delete, and escape will be handled on keyup
            // to accommodate Chrome.
            if (e.which === 8 || e.which === 46 || e.which === 27) {
                return;
            }

            buffer = buffer + String.fromCharCode(e.which);
            buffer = buffer.slice(0, settings.bufferLength);

            match();
        });

        return this;
    };
}(jQuery));
