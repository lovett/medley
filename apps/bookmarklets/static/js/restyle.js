// inspired by http://www.eahanson.com/2009/02/28/a-bookmarklet-to-reload-a-pages-css/

RESTYLE = (function() {
    'use strict';

    var scripts, frames, this_script, new_script, links, i;
    
    console.log('Adding restyle.js to ' + document.location.href);

    scripts = document.getElementsByTagName('script');
    frames = document.getElementsByTagName('frame');


    if (frames.length > 0) {
        console.log('This page has a frameset. Adding restyle.js to each frame.');

        for (i=0; i < scripts.length; i++) {
            if (scripts[i].src.indexOf('restyle.js') != -1) {
                this_script = scripts[i];
                break;
            }
        }

        for (i=0; i < frames.length; i++) {
            new_script = frames[i].contentWindow.document.createElement('script');
            new_script.setAttribute('src', this_script.src);
            frames[i].contentWindow.document.body.appendChild(new_script);
        }

        return;
    }

    links = document.getElementsByTagName('link');

    for (i = 0; i < links.length; i++) {
        if (links[i].rel == 'stylesheet') {
            if (links[i].href.indexOf("?") == -1) {
                links[i].href += '?';
            }
            links[i].href += 'x';
        }
    }
    
 
}())