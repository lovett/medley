MEDLEY.shortcuts = (function () {

    function adjustQueryDate(query, dayStep) {
        const matches = query.match(/date (.*)/);

        if (!matches) {
            return query;
        }

        let initialDate = Date.now();
        const oneDay = 86400000;

        if (matches[1] === 'yesterday') {
            initialDate -= oneDay;
        }

        const ymd = matches[1].match(/(\d\d\d\d)-(\d\d)-(\d\d)/);
        if (ymd) {
            initialDate = new Date(
                parseInt(ymd[1], 10),
                parseInt(ymd[2], 10) - 1,
                parseInt(ymd[3], 10)
            ).getTime();
        }

        const steppedDate = new Date(initialDate + (oneDay * dayStep));

        let steppedDateString = `${steppedDate.getFullYear()}-`;
        steppedDateString += `${(steppedDate.getMonth() + 1).toString().padStart(2, '0')}-`;
        steppedDateString += `${steppedDate.getDate().toString().padStart(2, '0')}`;

        query = query.replace(/^\s*date.*\s*/g, '');
        query = `date ${steppedDateString}\n${query}`;
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

        if (e.target.nodeName === 'BUTTON') {
            const form = e.target.closest('FORM');
            if (form) {
                form.submit();
            }
        }
    }

    return {
        init: function () {
            document.addEventListener('click', dispatchClick);
        }
    }
})();

window.addEventListener('DOMContentLoaded', MEDLEY.shortcuts.init);
