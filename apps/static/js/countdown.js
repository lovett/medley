MEDLEY.countdown = (function () {

    let instances = [];
    let timerId = 0;

    function refresh(instance) {
        const element = instance[0];
        const remainingSeconds = (instance[1] - new Date()) / 1000;

        let bag = []

        if (remainingSeconds < 0) {
            element.innerText = '';
            instances = instances.filter(x => x != instance);

            const hideClosest = element.dataset.hideClosest;
            if (hideClosest) {
                element.closest(hideClosest).hidden = true;
            }

            return;
        }

        let interval = Math.floor(remainingSeconds / 3600);
        if (interval > 0) {
            bag.push(interval);
            if (interval === 1) {
                bag.push('hour')
            }

            if (interval > 1) {
                bag.push('hours');
            }
        }

        interval = Math.floor((remainingSeconds % 3600) / 60);
        if (interval > 0) {
            bag.push(interval);
            if (interval === 1) {
                bag.push('minute');
            }

            if (interval > 1) {
                bag.push('minutes');
            }
        }

        interval = Math.floor(remainingSeconds % 60);
        if (interval > 0) {
            bag.push(interval);
            if (interval === 1) {
                bag.push('second');
            } else {
                bag.push('seconds');
            }
        }

        if (bag.length > 0) {
            bag.unshift('in');
        }

        element.innerText = bag.join(' ');
    }

    return {
        init: function () {
            timers = document.getElementsByClassName('countdown');

            if (!timers) {
                return;
            }

            Array.from(timers).forEach((timer) => {
                instances.push([
                    timer,
                    new Date(timer.dataset.expirationSeconds * 1000)
                ]);
            });


            if (instances.length === 0) {
                return;
            }

            timerId = setInterval(() => {
                instances.forEach(instance => refresh(instance));
                if (instances.length === 0) {
                    clearInterval(timerId);
                }
            }, 1000);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.countdown.init);
