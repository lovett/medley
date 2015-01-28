(function ($) {
    $.fn.focusAsYouType = function(options) {
        var buffer = '';
        var settings = $.extend({
            bufferLength: 5,
            candidateClass: 'focus-candidate'
        }, options);

        var elements = jQuery(this);

        var candidates = elements.map(function (index, el) {
            var text = $(el).text().trim();

            text = text.split('\n').shift().toLowerCase();
            return text;
        }).get();

        $(document).on('keypress', function (e) {
            buffer = buffer + String.fromCharCode(e.which);
            buffer = buffer.slice(0, settings.bufferLength);

            var matches = candidates.map(function (candidate) {
                if (candidate.indexOf(buffer) == 0) {
                    return 1;
                } else {
                    return 0;
                }
            });

            var score = matches.reduce(function (accumulator, value) {
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
            };
        });

        setInterval(function () {
            buffer = '';
        }, 3000);
        return this;
    };
}(jQuery));
