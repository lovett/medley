MEDLEY.shortcuts = (function () {

    function urlRemovePath(value) {
        const node = document.createElement('a');
        node.href = value.trim()
        node.pathname = '';
        return node.href;
    }

    function urlRemoveQuery(value) {
        const node = document.createElement('a');
        node.href = value.trim()
        node.search = '';
        return node.href;
    }

    function urlRemoveHash(value) {
        const node = document.createElement('a');
        node.href = value.trim()
        node.hash = '';
        return node.href;
    }

    function sentenceTrimStart(value) {
        return value.replace(/^(.*?\.) ([A-Z].*)/m, '$2');
    }

    function sentenceTrimEnd(value) {
        return value.replace(/^(.*\.) ([A-Z].*)/m, '$1');
    }

    function dispatchClick(e) {
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

        if (shortcut === 'url-remove-path') {
            field.value = urlRemovePath(field.value);
        }

        if (shortcut === 'url-remove-hash') {
            field.value = urlRemoveHash(field.value);
        }

        if (shortcut === 'url-remove-query') {
            field.value = urlRemoveQuery(field.value);
        }

        if (shortcut === 'sentence-trim-start') {
            field.value = sentenceTrimStart(field.value);
        }

        if (shortcut === 'sentence-trim-end') {
            field.value = sentenceTrimEnd(field.value);
        }
    }

    return {
        init: function () {
            document.addEventListener('click', dispatchClick);
        }
    }
})();

window.addEventListener('DOMContentLoaded', MEDLEY.shortcuts.init);
