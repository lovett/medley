MEDLEY.shortcuts = (function () {

    function adjustQueryDate(query, dayStep) {
        const matches = query.match(/date (.*)/);

        if (!matches) {
            return value;
        }

        let initialDate = new Date();

        if (matches[1] === 'yesterday') {
            initialDate = new Date(Date.now() - 86400000);
        }

        if (matches[1].match(/\d\d\d\d-\d\d-\d\d/)) {
            initialDate = new Date(matches[1]);
        }

        const newDate = new Date(initialDate.getTime() + 86400000 * dayStep);

        const newDateString = newDate.toISOString().replace(/T.*/, '')

        query = query.replace(/^\s*date.*\s*/g, '');
        query = 'date ' + newDateString + '\n' + query;
        return query;
    }

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

        if (shortcut === 'query-date-forward') {
            field.value = adjustQueryDate(field.value, 1);
        }

        if (shortcut === 'query-date-backward') {
            field.value = adjustQueryDate(field.value, -1);
        }
    }

    return {
        init: function () {
            document.addEventListener('click', dispatchClick);
        }
    }
})();

window.addEventListener('DOMContentLoaded', MEDLEY.shortcuts.init);
