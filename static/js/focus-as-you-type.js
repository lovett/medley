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

        $(document).on('keypress', function (e) {
            var matches, now, score;

            if (e.which === 27) { // escape key
                clearBuffer();
                return;
            }

            if (e.which === 8 || e.which === 46) { // backspace, delete
                buffer = buffer.slice(0, buffer.length - 1);
            } else {
                buffer = buffer + String.fromCharCode(e.which);
                buffer = buffer.slice(0, settings.bufferLength);
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
        });

        return this;
    };
}(jQuery));
