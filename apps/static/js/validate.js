'use strict';

var VALIDATOR = (function() {
    var endpoint, request;

    endpoint = 'http://validator.w3.org/check';
    request = new XMLHttpRequest();

    return {
        init: function() {
            VALIDATOR.requestCurrentPage();
        },

        requestCurrentPage: function() {
            request.open('GET', window.location, true);
            request.onreadystatechange = function() {
                if (request.readyState !== 4) {
                    return;
                }
                if (request.status !== 200 && request.status !== 304) {
                    alert('HTTP error ' + request.status);
                    return;
                }
                VALIDATOR.submit(request.responseText);
            };
            request.send();
        },

        submit: function(page_source) {
            var form_id, node, form, fragment_field;
            // if the form is already on the page, remove it
            form_id = 'validator-form';
            node = document.getElementById(form_id);
            if (node) {
                node.parentNode.removeChild(node);
            }

            // append a form to the page
            form = document.createElement('form');
            form.setAttribute('id', form_id);
            form.setAttribute('method', 'post');
            form.setAttribute('enctype', 'multipart/form-data');
            form.setAttribute('action', endpoint);
            form.setAttribute('style', 'position:absolute;display:none');

            fragment_field = document.createElement('textarea');
            fragment_field.setAttribute('name', 'fragment');
            fragment_field.setAttribute('cols', '100');
            fragment_field.setAttribute('rows', '100');
            fragment_field.appendChild(document.createTextNode(page_source));
            form.appendChild(fragment_field);

            document.body.appendChild(form);

            form.submit();
        }
    };
}());

VALIDATOR.init();
