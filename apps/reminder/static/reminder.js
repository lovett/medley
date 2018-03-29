MEDLEY.reminders = (function () {
    'use strict';

    var timer, timeLabels = {};

    function deleteTemplate(e) {
        var option, uid;
        e.preventDefault();
        uid = parseInt(jQuery(this).data('uid'), 10) || 0;

        jQuery.ajax({
            type: 'DELETE',
            url: '/registry?uid=' + uid
        }).fail(function () {
            alert('The reminder could not be deleted');
        }).done(function (data) {
            window.location.reload();
        });
    }

    function deleteReminder(e) {
        var reminder, trigger, uid;
        e.preventDefault();

        trigger = jQuery(this);
        reminder = trigger.closest('.upcoming-reminder');

        if (reminder.hasClass('done')) {
            reminder.hide();
            return;
        }

        uid = trigger.data('uid');

        jQuery.ajax({
            type: 'DELETE',
            url: '/reminder?uid=' + uid
        }).done(function (data) {
            window.location.reload();
        });
    }


    function remaining(ms) {
        var seconds, bag, seconds, interval;

        seconds = (ms - Date.now()) / 1000;
        bag = []

        interval = Math.floor(seconds / 3600);
        if (interval > 0) {
            bag.push(interval);
            if (interval === 1) {
                bag.push(timeLabels.hour[0]);
            } else {
                bag.push(timeLabels.hour[1]);
            }
        }

        interval = Math.floor((seconds % 3600) / 60);
        if (interval > 0) {
            bag.push(interval);
            if (interval === 1) {
                bag.push(timeLabels.minute[0]);
            } else {
                bag.push(timeLabels.minute[1]);
            }
        }

        interval = Math.floor(seconds % 60);
        if (interval > 0) {
            bag.push(interval);
            if (interval === 1) {
                bag.push(timeLabels.second[0]);
            } else {
                bag.push(timeLabels.second[1]);
            }
        }

        if (bag.length > 0) {
            bag.unshift(timeLabels['in'][0]);
            return bag.join(' ');
        }

        return '';
    }

    function countdown() {
        var now = Date.now();
        var times = jQuery('#scheduled-reminders time').map(function() {
            return jQuery(this);
        });

        if (times.length === 0) {
            jQuery('#scheduled-reminders').remove();
            clearInterval(timer);
            return;
        }

        times.each(function (index, time) {
            var expiration, ms;
            ms = parseFloat(time.attr('datetime'));
            expiration = remaining(ms);

            if (expiration === '') {
                time.closest('.upcoming-reminder').remove();
            }

            time.nextAll('.remaining').html(expiration);
        });
    }

    return {
        init: function () {
            jQuery('.summary').on('click', function () {
                var template = jQuery(this);
                jQuery('INPUT, TEXTAREA').each(function () {
                    var id = this.getAttribute('id');
                    var val = template.data(id);
                    if (val) {
                        jQuery(this).val(val);
                    }
                });

                jQuery('#reminder-form').submit();
            });

            jQuery('.delete-template').on('click', deleteTemplate);
            jQuery('.delete-reminder').on('click', deleteReminder);

            jQuery('meta[name^="lang.time"]').each(function (index, el) {
                var key, node, value;
                node = jQuery(el);
                key = node.attr('name').split('.').pop();
                value = node.attr('content').split(',');
                timeLabels[key] = value;
            });
            timer = setInterval(countdown, 1000);
        }
    }
}());

jQuery(document).ready(MEDLEY.reminders.init);
