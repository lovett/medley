MEDLEY.startpage = (function () {
    'use strict';

    let anonymizerUrl = null;
    let pageLinks = [];

    /**
     * Open multiple links at once.
     */
    function openLinkGroup(e) {
        if (e.target.className !== 'all') {
            return;
        }

        e.preventDefault();

        const links = e.target.parentNode.getElementsByTagName('A');

        for (let i=1; i < links.length; i++) {
            if (links[i] === e.target) {
                continue;
            }
            window.open(links[i].getAttribute('href'));
        }

        window.location.href = links[0].getAttribute('href');
    }

    /**
     * Prefix or unprefix the anonymizer URL from eligible links.
     */
    function toggleAnonymizer (e) {
        for (let i=0; i < pageLinks.length; i++) {
            const link = pageLinks[i];
            if (parseInt(link.dataset.anonable, 10) === -1) {
                continue;
            }

            let href = decodeURIComponent(link.getAttribute('href'));
            href = href.replace(anonymizerUrl, '');

            if (e.target.checked) {
                href = anonymizerUrl + encodeURIComponent(href);
            }

            link.setAttribute('href', href);
        }
    }

    return {
        init: function () {
            pageLinks = document.getElementsByTagName('A');

            // Determine the anonymizer URL
            const nodes = document.getElementsByTagName('META');
            for (let i=0; i < nodes.length; i++) {
                if (nodes[i].getAttribute('name') === 'anonymizer') {
                    anonymizerUrl = nodes[i].getAttribute('content');
                    break;
                }
            }

            if (anonymizerUrl) {
                const anonymizeCheckbox = document.getElementById('anonymize');
                anonymizeCheckbox.removeAttribute('disabled');
                anonymizeCheckbox.setAttribute('checked', true);

                // Links that are not initially anonymized should always remain so
                for (let i=0; i < pageLinks.length; i++) {
                    const href = pageLinks[i].getAttribute('href');
                    pageLinks[i].dataset.anonable = href.indexOf(anonymizerUrl);
                }

                anonymizeCheckbox.addEventListener('click', toggleAnonymizer);
            }

            // Tag link groups
            const lis = document.getElementsByTagName('LI');
            const groupTrigger = document.createElement('A');
            groupTrigger.setAttribute('href', '#all');
            groupTrigger.setAttribute('class', 'all');
            groupTrigger.innerText = '[all]';

            for (let i=0; i < lis.length; i++) {
                if (lis[i].getElementsByTagName('A').length > 1) {
                    lis[i].setAttribute('class', 'group');
                    lis[i].appendChild(groupTrigger.cloneNode(true));
                }
            }

            document.addEventListener('click', openLinkGroup);

            MEDLEY.focusAsYouType('SECTION A');
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.startpage.init);
