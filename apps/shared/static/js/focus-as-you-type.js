MEDLEY.focusAsYouType = (function () {
    'use strict';

    const DEFAULTS = {
        bufferLength: 10,
        candidateClass: 'focus-candidate',
        bufferDisplaySelector: '.focus-buffer-display'
    };

    let buffer = '';
    let bufferDisplay = null;
    let elements = [];
    let candidates = [];
    let options = {}
    let matchCount = 0;

    function ignorable(e) {
        if (e.target.nodeName === 'INPUT') {
            return true;
        }

        if (e.target.nodeName === 'TEXTAREA') {
            return true;
        }

        return false;
    }

    function clearBuffer() {
        buffer = '';
        matchCount = 0;
        elements.forEach((element) => {
            element.classList.remove(options.candidateClass);
            element.blur();
        });
        displayBuffer();
    }

    function displayBuffer() {
        if (matchCount == 0) {
            bufferDisplay.innerText = buffer;
        }

        if (matchCount == 1) {
            bufferDisplay.innerText = `${buffer} - 1 match`;
        }

        if (matchCount > 1) {
            bufferDisplay.innerText = `${buffer} - ${matchCount} matches`;
        }
    }

    function match() {
        if (buffer === '') {
            clearBuffer();
            return;
        }

        displayBuffer();

        let matches = candidates.map(function (candidate) {
            return (candidate.indexOf(buffer) === 0)? 1 : 0;
        });

        matchCount = matches.reduce(function (accumulator, value) {
            return accumulator + value;
        });

        elements.forEach((element) => {
            element.classList.remove(options.candidateClass);
        })

        if (matchCount == 1) {
            elements[matches.indexOf(1)].focus();
        }

        matches.forEach(function (match, index) {
            if (match === 1) {
                elements[index].classList.add(options.candidateClass);
            }
        });
    }

    // Chrome won't send keypress events for non-printable
    // keys. Handle them on keyup instead.
    function onKeyUp(e) {
        if (ignorable(e)) {
            return;
        }

        if (e.target.nodeName === 'TEXTAREA') {
            return;
        }

        if (e.which === 13) { // enter key
            return;
        }

        if (e.which === 27) { // escape key
            clearBuffer();
            return;
        }

        if (e.which === 8 || e.which === 46) { // backspace, delete
            buffer = buffer.slice(0, buffer.length - 1);
            match();
        }
    }

    function onKeyPress(e) {
        if (ignorable(e)) {
            return;
        }

        // Backspace, delete, and escape will be handled on keyup
        // to accommodate Chrome.
        if (e.which === 8 || e.which === 46 || e.which === 27) {
            return;
        }

        // Take no action when the control or alt keys are being pressed.
        if (e.ctrlKey || e.altKey || e.shiftKey) {
            return;
        }

        // Take no action when the enter is is being pressed.
        if (e.which === 13) {
            return;
        }

        buffer = buffer + String.fromCharCode(e.which);
        buffer = buffer.slice(0, options.bufferLength);
        match();
    }

    return function (selector, customOptions={}) {
        options = Object.assign(DEFAULTS, customOptions);
        elements = Array.from(document.querySelectorAll(selector));

        bufferDisplay = document.querySelector(
            options.bufferDisplaySelector
        );

        candidates = elements.map((el) => {
            let text = el.innerText.trim()
            return text.split('\n').shift().toLowerCase();
        });

        document.addEventListener('keyup', onKeyUp);
        document.addEventListener('keypress', onKeyPress);
    }
})();
