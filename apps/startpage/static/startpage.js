// Display the last modified time of the data file
var el = document.getElementById('modified');

if (el) {
    var dt_string;
    var dt = new Date(Date.parse(el.getAttribute('datetime')));
    dt_string = dt.toLocaleString();

    // remove seconds, timezone, and year
    dt_string = dt_string.replace(/(\d\d):\d\d ([AP]M).*/, "$1 $2");
    dt_string = dt_string.replace(', ' + (new Date().getYear() + 1900), '');
    el.innerHTML = 'Updated ' + dt_string;
}

// Determine the anonymizer URL
var meta = document.getElementsByTagName('META');
var anonymizer_url;
var i;
for (i=0; i < meta.length; i++) {
    if (meta[i].getAttribute('name') === 'anonymizer') {
        anonymizer_url = meta[i].getAttribute('content');
        break;
    }
}

// Activate or deactivate the anonymizer URL
var anonymize = document.getElementById('anonymize');
if (anonymize && anonymizer_url) {
    var links = document.getElementsByTagName('A');
    anonymize.removeAttribute('disabled');
    anonymize.setAttribute('checked', true);

    // Links that are not initially anonymized should always remain so
    for (i=0; i < links.length; i++) {
        href = links[i].getAttribute('href');
        links[i].setAttribute('data-anonable', href.indexOf(anonymizer_url));
    }

    function clickListener () {
        for (i=0; i < links.length; i++) {
            if (parseInt(links[i].getAttribute('data-anonable'), 10) === -1) {
                continue;
            }

            href = decodeURIComponent(links[i].getAttribute('href'));
            href = href.replace(anonymizer_url, '');
            if (this.checked) {
                href = anonymizer_url + encodeURIComponent(href);
            }
            links[i].setAttribute('href', href);
        }
    }

    if (anonymize.attachEvent) {
        anonymize.attachEvent('onclick', clickListener);
    } else {
        anonymize.addEventListener('click', clickListener);
    }
}

// Open all links in a group
function openGroup(e) {
    var container, i, href, links, newWindow;

    if (!e.target) {
        return;
    }

    if (e.target.className !== 'all') {
        return;
    }

    e.preventDefault();

    links = e.target.parentNode.getElementsByTagName('A');
    for (i=1; i < links.length; i++) {
        if (links[i] === e.target) continue;
        href = links[i].getAttribute('href');
        window.open(href);
    }
    window.location.href = links[0].getAttribute('href');
}

// Tag link groups
var lis = document.getElementsByTagName('LI');
var groupTrigger = document.createElement('A');
groupTrigger.setAttribute('href', '#all');
groupTrigger.setAttribute('class', 'all');
groupTrigger.innerText = '[all]';

for (i=0; i < lis.length; i++) {
    if (lis[i].getElementsByTagName('A').length > 1) {
        lis[i].setAttribute('class', 'group');
        lis[i].appendChild(groupTrigger.cloneNode(true));
    }
}

if (anonymize && anonymize.attachEvent) {
    document.getElementsByTagName('MAIN')[0].attachEvent('click', openGroup);
} else {
    document.getElementsByTagName('MAIN')[0].addEventListener('click', openGroup);
}

// Highlight the active section
var fragment = window.location.hash.replace('#', '');
if (fragment.length > 0) {
    document.getElementById(fragment).classList.add('active');
}

jQuery('SECTION A, SECTION H1').focusAsYouType();

// Hide the edit link when offline
var onlineOnly = document.querySelectorAll('.online-only');
var offlineOnly = document.querySelectorAll('.offline-only');

var whenOffline = function () {
    for (i=0; i < onlineOnly.length; i++) {
        onlineOnly[i].classList.add('hidden');
    }

    for (i=0; i < offlineOnly.length; i++) {
        offlineOnly[i].classList.remove('hidden');
    }
}

var whenOnline = function () {
    for (i=0; i < onlineOnly.length; i++) {
        onlineOnly[i].classList.remove('hidden');
    }

    for (i=0; i < offlineOnly.length; i++) {
        offlineOnly[i].classList.add('hidden');
    }
}

window.addEventListener('offline', whenOffline);
window.addEventListener('online', whenOnline);

if (navigator.onLine === false) {
    whenOffline();
}
