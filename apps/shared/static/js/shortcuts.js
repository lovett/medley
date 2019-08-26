MEDLEY.shortcuts = (function () {
    function shortcutClick(e) {
        if (!e.target.dataset.shortcut) {
            return;
        }

        if (!e.target.dataset.field) {
            return;
        }

        e.preventDefault();

        const shortcut = e.target.dataset.shortcut;
        const field = document.getElementById(e.target.dataset.field);

        if (!field) {
            return;
        }

        if (shortcut === 'set-value') {
            field.value = e.target.dataset.value;
        }
    }

    return {
        init: function () {
            document.addEventListener('click', shortcutClick);
        }
    }
})();

window.addEventListener('DOMContentLoaded', MEDLEY.shortcuts.init);
