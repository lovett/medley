MEDLEY.startpage = (function () {
    'use strict';

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

    return {
        init: function () {
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
