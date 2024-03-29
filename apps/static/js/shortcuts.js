MEDLEY.shortcuts = (function () {

    function standardDateString(d) {
        result = `${d.getFullYear()}-`;
        result += `${(d.getMonth() + 1).toString().padStart(2, '0')}-`;
        result += `${d.getDate().toString().padStart(2, '0')}`;
        return result;
    }

    function standardTimeString(d) {
        return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    }

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

        let steppedDateString = standardDateString(steppedDate);
        query = query.replace(/^\s*date.*\s*/g, '');
        query = `date ${steppedDateString}\n${query}`;
        return query;
    }

    function replaceSelection(value, selectionStart, selectionEnd, search, replace) {
        let selection = value.substring(selectionStart, selectionEnd);

        if (selection.length === 0) {
            return value;
        }

        replacement = selection.replace(search, replace);

        return value.replace(selection, replacement);
    }

    function spliceText(target, value, appendNewline=false) {
        const insertIndex = target.selectionStart;
        const before = target.value.slice(0, insertIndex);
        const suffix = (appendNewline)? " \n" : "";
        const after = target.value.slice(insertIndex);

        target.value = before + value + suffix + after;

        target.focus();

        const newSelectionStart = insertIndex + value.length + 1;
        target.setSelectionRange(newSelectionStart, newSelectionStart);
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

        if (shortcut === 'clear') {
            field.value = '';
        }

        if (shortcut === 'append-value') {
            let value = field.value.trim()

            while (value.endsWith(e.target.dataset.delimiter)) {
                value = value.slice(0, -1);
            }

            if (value) {
                value += e.target.dataset.delimiter + ' ';
            }

            value += e.target.dataset.value;

            field.value = value;
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

        if (shortcut === 'markdown-list') {
            field.value = field.value.replace(
                /^\s+[\r\n]/gm,
                ''
            );

            field.value = replaceSelection(
                field.value,
                field.selectionStart,
                field.selectionEnd,
                /^[\s\-\*]*/gm,
                "- "
            );
        }

        if (shortcut === 'unwrap') {
            field.value = replaceSelection(
                field.value,
                field.selectionStart,
                field.selectionEnd,
                /([^\r\n])[\r\n](?![\s\n]+)/gm,
                '$1 '
            );
        }

        if (shortcut === 'spaced-sentences') {
            field.value = replaceSelection(
                field.value,
                field.selectionStart,
                field.selectionEnd,
                /(\w)\.\s*(\w)/gm,
                "$1.\n\n$2"
            );
        }

        if (shortcut === 'today') {
            field.value = standardDateString(new Date());
        }

        if (shortcut === 'now') {
            field.value = standardTimeString(new Date());
        }

        if (shortcut === 'yesterday') {
            const dt = new Date();
            dt.setDate(dt.getDate() - 1);
            field.value = standardDateString(dt);
        }

        if (e.target.nodeName === 'BUTTON') {
            const form = e.target.closest('FORM');
            if (form) {
                form.submit();
            }
        }
    }

    function dispatchChange(e) {
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

        if (shortcut === 'splice-to-newline') {
            if (e.target.value) {
                spliceText(field, e.target.value, true);
                e.target.value = '';
            }
        }

    }

    return {
        init: function () {
            document.addEventListener('click', dispatchClick);
            document.addEventListener('change', dispatchChange);
        }
    }
})();

window.addEventListener('DOMContentLoaded', MEDLEY.shortcuts.init);
