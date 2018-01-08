var HNHIRING = (function () {
    'use strict';

    var tables, panel, child, cells, lastRun;

    lastRun = localStorage.getItem('hn-filter-lastrun');
    if (lastRun) {
        lastRun = parseInt(lastRun, 10);
    }

    cells = document.querySelectorAll('td.default');

    panel = document.getElementById('hn-filter');

    if (panel) {
        panel.parentNode.removeChild(panel);
    }

    panel = document.createElement('form');
    panel.setAttribute('id', 'hn-filter');
    panel.setAttribute('style', 'color:black;background-color: LightBlue;padding:1em');


    child = document.createElement('a');
    child.setAttribute('style', 'display:block;float:right;font-size:.85em;');
    child.setAttribute('href', '#close');
    child.textContent = 'close';
    child.addEventListener('click', closePanel, false);
    panel.appendChild(child);

    child = document.createElement('a');
    child.setAttribute('style', 'display:block;float:right;font-size:.85em;margin-right:2em');
    child.setAttribute('href', '#help');
    child.textContent = 'help';
    child.addEventListener('click', toggleHelp, false);
    panel.appendChild(child);

    child = document.createElement('legend');
    child.setAttribute('style', 'font-weight: bold;margin-bottom:.5em');
    child.innerHTML = 'HN Hiring Filter';
    panel.appendChild(child);

    child = document.createElement('div');
    child.setAttribute('id', 'hn-filter-help');
    panel.appendChild(child);

    child = document.createElement('label');
    child.setAttribute('style', 'display:block');
    child.setAttribute('for', 'hn-filter-include');
    child.textContent = 'Include keywords:';
    panel.appendChild(child);

    child = document.createElement('textarea');
    child.setAttribute('style', 'margin-bottom: 1em;width:100%;min-height:5em;');
    child.setAttribute('type', 'text');
    child.setAttribute('id', 'hn-filter-include');
    child.textContent = localStorage.getItem('hn-filter-include');
    panel.appendChild(child);

    child = document.createElement('label');
    child.setAttribute('style', 'display:block');
    child.setAttribute('for', 'hn-filter-exclude');

    child.textContent = 'Exclude keywords:';
    panel.appendChild(child);

    child = document.createElement('textarea');
    child.setAttribute('style', 'margin-bottom: 1em;width:100%;min-height:5em;');
    child.setAttribute('type', 'text');
    child.setAttribute('id', 'hn-filter-exclude');
    child.textContent = localStorage.getItem('hn-filter-exclude');
    panel.appendChild(child);

    /*
    if (lastRun) {
        child = document.createElement('input');
        child.setAttribute('type', 'checkbox');
        child.setAttribute('name', 'hn-filter-today');
        child.setAttribute('id', 'hn-filter-since-');
        child.setAttribute('value', lastRun);
        child.setAttribute('checked', 'checked');
        panel.appendChild(child);

        child = document.createElement('label');
        child.setAttribute('for', 'hn-filter-since-lastrun');
        child.innerHTML = 'Posted since <time></time>';
        formatDate(child.getElementsByTagName('TIME')[0], lastRun);
        panel.appendChild(child);
    }
    */


    child = document.createElement('button');
    child.setAttribute('style', 'display:block;margin-top:1em');
    child.textContent = 'Run';
    panel.appendChild(child);

    child = document.createElement('div');
    child.setAttribute('id', 'hn-filter-message');
    child.setAttribute('style', 'font-size:.85em;color:black;text-align:center');
    panel.appendChild(child);


    panel.addEventListener('submit', applyFilter, false);

    if (document.getElementsByTagName('TEXTAREA').length > 0) {
        document.getElementsByTagName('FORM')[0].parentNode.appendChild(panel);
    } else {
        tables = document.getElementsByTagName('TABLE');
        tables[2].parentNode.insertBefore(panel,  tables[2].nextSibling.nextSibling);
    }

    document.getElementById('hn-filter-include').focus();

    if (document.getElementById('hn-filter-include').value !== '' ||
        document.getElementById('hn-filter-exclude').value !== '') {
        panel.dispatchEvent(new Event('submit'));
    }

    function closePanel (e) {
        e.preventDefault();
        panel.parentNode.removeChild(panel);
    }

    function toggleHelp (e) {
        e.preventDefault();

        var target = document.getElementById('hn-filter-help');
        if (target.innerHTML !== '') {
            target.innerHTML = '';
            return;
        }

        target.innerHTML = '<p>Posts will be matched if they contain <strong>all</strong> the Include keywords.</p>';
        target.innerHTML += '<p>Posts will be hidden if they contain <strong>any</strong> of the Exclude keywords.</p>';
        target.innerHTML += '<p>Separate keywords with spaces. Use quotes around multi-word phrases.</p>';

    }

    function displayMessage (message) {
        document.getElementById('hn-filter-message').innerHTML = '<p>' + message + '</p>';
    }

    function clearMessage () {
        document.getElementById('hn-filter-message').innerHTML = '';
    }

    function extractTerms (value) {
        var phrases, words, terms;

        value = value.replace(/[\r\n]+/g, ' ');

        // quoted phrases
        phrases = value.match(/".*?"/g) || [];
        phrases = phrases.map(function (p) {
            value = value.replace(p, '');
            return p.replace(/"/g, '');
        });

        // single words
        words = value.replace(/\s+/g, ' ').trim().split(' ');

        return phrases.concat(words);
    }

    function applyFilter (e) {
        var counters, message;
        e.preventDefault();
        clearMessage();
        var include, exclude;
        include = document.getElementById('hn-filter-include');
        exclude = document.getElementById('hn-filter-exclude');
        counters = {
            visible: 0,
            hidden: 0
        };

        localStorage.setItem('hn-filter-lastrun', new Date().getTime());
        localStorage.setItem('hn-filter-include', include.value);
        localStorage.setItem('hn-filter-exclude', exclude.value);

        if (include.value === '' && exclude.value == '') {
            displayMessage('No filters specified.');
            return;
        }

        include = extractTerms(include.value);
        exclude = extractTerms(exclude.value);

        for (var i=0; i < cells.length; i++) {
            var cell = cells[i];
            var row  = cell.parentNode;
            var spacer = row.getElementsByTagName('IMG');
            var text = row.textContent.toLowerCase();

            var parent = row.parentNode.parentNode.parentNode.parentNode;
            var valid = true;
            var counterIncrement = 1;

            // the cell is valid if all inclusion keywords match
            include.forEach(function (term) {
                if (term === '') {
                    return;
                }

                if (valid === true) {
                    valid = text.indexOf(term.toLowerCase()) > -1;
                }
            });

            // the cell is invalid if at least one exclusion keyword matches
            exclude.some(function (term) {
                if (term === '') {
                    return;
                }

                if (text.indexOf(term.toLowerCase()) > -1) {
                    valid = false;
                    return true;
                }
            });

            // the cell is invalid if it is a reply
            if (spacer.length > 0 && parseInt(spacer[0].getAttribute('width')) > 0) {
                valid = false;
                counterIncrement = 0;
            }

            if (valid) {
                // highlight all inclusion keywords
                include.forEach(function (term, index) {
                    if (term === '') {
                        return;
                    }
                    highlight(cell, term, index);
                });
                parent.setAttribute('style', 'display:table');

                counters.visible = counters.visible + counterIncrement;
            } else {
                unhighlight(cell);
                parent.setAttribute('style', 'display:none');
                counters.hidden = counters.hidden + counterIncrement;
            }

            message = 'Matched ' + counters.visible + ((counters.visible === 1)? ' post':' posts') + '. ';
            message += 'Hid ' + counters.hidden + ((counters.hidden === 1)? ' post':' posts') + '.';
            displayMessage(message);
        }
    };

    function highlight(node, term, colorIndex) {
        var palette, color, re, reReplacement, walker, textValues, finalReplacement;

        palette = ['green', 'orange', 'blue', 'purple'];
        color = palette[colorIndex] || palette[0];
        re = new RegExp("\\b\(" + term + "\)\\b", 'gi');
        reReplacement = '<span class="hn-filter-highlight" style="font-weight:bold;background-color:'+color+';color:white">$1</span>';

        walker = document.createTreeWalker(node, window.NodeFilter.SHOW_TEXT, {
            acceptNode: function (node) {
                if ( node.data.indexOf('http') !== 0) {
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        }, false);


        textValues = [];
        while (walker.nextNode()) {
            textValues.push(walker.currentNode.textContent);
        }


        finalReplacement = node.innerHTML;

        textValues.forEach(function (textValue) {
            var replacement = textValue.replace(re, reReplacement);
            finalReplacement = finalReplacement.replace(textValue, replacement);
        });

        node.innerHTML = finalReplacement;



    };

    function unhighlight(node) {
        node.innerHTML = node.innerHTML.replace(/<span class="hn-filter-highlight".*?>(.*)<\/span>/g, '$1');
    };

    function formatDate(node, timestamp) {
        var d, result;


        d = new Date(timestamp);
        result = [];


        result.push(d.getHours());
        result.push(d.getMinutes());
        if (result[0] > 12) {
            result.push('PM');
            result[0] -= 12;
        } else {
            result.push('AM');
        }

        if (result[1] < 10) {
            result[1] = '0' + result[1];
        }

        result.push(d.getMonth() + 1);
        result.push(d.getDate());
        result.push(d.getYear() + 1900);

        if (result[3] < 10) {
            result[3] = '0' + result[3];
        }

        if (result[4] < 10) {
            result[4] = '0' + result[4];
        }

        node.textContent = result.slice(0, 2).join(':') + ' ' + result[2] + ' on ' + result.slice(3).join('/');
    };

})();
