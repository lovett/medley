// querystring parsing taken from http://feather.elektrum.org/book/src.html

var RESTATE = (function() {
    'use strict';

    var scripts, frames, querystring, querystring_pairs, i, this_script, new_script,
    util, keyval, key, val, qs, domain_segments, domain_root, i, task_script, Task,
    processQueue, queue, queue_interval;

    console.log('Adding restate.js to ' + document.location.href);

    scripts = document.getElementsByTagName('script');
    frames = document.getElementsByTagName('frame');

    for (i=0; i < scripts.length; i++) {
        if (scripts[i].src.indexOf('restate.js') != -1) {
            querystring = scripts[i].src.replace(/^[^\?]+\??/, '');
            break;
        }
    }

    qs = {};

    querystring_pairs = querystring.split(/[;&]/);

    for (i = 0; i < querystring_pairs.length; i = i + 1) {
        keyval = querystring_pairs[i].split('=');
        if (keyval.length === 2) {
            key = decodeURIComponent(keyval[0]);
            val = decodeURIComponent(keyval[1]);
            qs[key] = val.replace(/\+/g, ' ');
        }
    }

    if (!qs.hasOwnProperty('r')) {
        console.error('The querystring on restate.js does not contain a key named "r"');
        console.error('The "r" key should point to the URL that restate.js will load its task scripts from');
        return;
    } else if (!qs.hasOwnProperty('d')) {
        console.error('The querystring on restate.js does not contain a key named "d"');
        console.error('The "d" key should contain a timestamp that will prevent browser caching');
        return;
    } else if (frames.length > 0) {
        console.log('This page has a frameset. Adding restate.js to each frame.');

        for (i=0; i < scripts.length; i++) {
            if (scripts[i].src.indexOf('restate.js') != -1) {
                this_script = scripts[i];
                break;
            }
        }

        for (i=0; i < frames.length; i++) {
            new_script = frames[i].contentWindow.document.createElement('script');
            new_script.setAttribute('src', this_script.src);
            frames[i].contentWindow.document.body.appendChild(new_script);
        }
    } else {
        // The task script's file name is derived from location.host
        // based on some educated guessing.
        domain_segments = location.host.split('.');
        if (domain_segments.length < 3) {
            domain_root = domain_segments[0];
        } else {
            for (i = domain_segments.length - 1; i > 0; i--) {
                if (domain_segments[i] == 'local') continue;
                if (domain_segments[i].length > 3) {
                    domain_root = domain_segments[i];
                    break;
                }
            }
        }
        
        task_script = document.createElement('script');
        
        task_script.setAttribute('src', qs.r + '/' + domain_root + '.js?d=' + qs.d);
        document.body.appendChild(task_script);
        console.log('Extending restate.js with tasks from ' + task_script.src);
    }
    
    Task = function() {
        this.before = function(message) {
            if (message) {
                console.log(message);
            }
        };

        this.after = function(message) {
            if (message) {
                console.log(message);
            }
        };

        this.action = null;
    };

    processQueue = function() {
        if (queue.length === 0) {
            return;
        }

        if (!(queue[0] instanceof Task)) {
            console.error('The current object in the task queue is not a Task instance. Halting the queue and giving up.');
            clearInterval(queue_interval);
            return;
        }

        if (typeof queue[0].before === 'function') {
            queue[0].before();
        }

        if (queue[0].action() === true) {
            if (typeof queue[0].after === 'function') {
                queue[0].after();
            }
            queue.shift();
        }
    };

    util = {
        randString: function(len) {
            var charSet, result, position, i;
            charSet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
            result = '';
            for (i = 0; i < len; i = i + 1) {
                position = Math.floor(Math.random() * charSet.length);
                result += charSet.substring(position, position + 1);
            }
            return result;
        },

        randNumber: function(len) {
            var result, position, i;
            result = '';
            for (i = 0; i < len; i = i + 1) {
                result += Math.floor(Math.random() * 9).toString();
            }
            return result;
        },

        hideElementById: function(hideables) {
            var i, target;

            if (typeof hideables == 'string') {
                hideables = [hideables];
            }

            for (i=0; i < hideables.length; i++) {
                target = document.getElementById(hideables[i]);
                if (target) target.style.display = 'none';
            }
        }
        
    };

    queue = [];
    queue_interval = setInterval(processQueue, 1000);

    return {
        'Task': Task,

        'util': util,

        'add': function(o) {
            var i;
            if (o instanceof Array) {
                for (i = 0; i < o.length; i = i + 1) {
                    queue.push(o[i]);
                }
            } else {
                queue.push(o);
            }
        }
    };

}());
