(function ($) {
    'use strict';
    $.fn.focusAsYouType = function(options) {
        var buffer, candidates, elements, settings;
        buffer = '';
        settings = $.extend({
            bufferLength: 2,
            candidateClass: 'focus-candidate'
        }, options);

        elements = jQuery(this);

        candidates = elements.map(function (index, el) {
            var text = $(el).text().trim();

            text = text.split('\n').shift().toLowerCase();
            return text;
        }).get();

        $(document).on('keypress', function (e) {
            var matches, score;
            buffer = buffer + String.fromCharCode(e.which);
            buffer = buffer.slice(0, settings.bufferLength);

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

        setInterval(function () {
            buffer = '';
            elements.removeClass(settings.candidateClass).blur();
        }, 4000);
        return this;
    };
}(jQuery));
