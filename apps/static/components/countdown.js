Vue.component('countdown', {
    props: {
        defaultLabel: {
            type: String,
            required: false,
            default: 'Calculating…'
        },
        expirationSeconds: {
            type: Number,
            required: true
        },
        hoursLabels: {
            type: Array,
            default: function () {
                return ['hours', 'hour'];
            }
        },
        minutesLabels: {
            type: Array,
            default: function () {
                return ['minutes', 'minute'];
            }
        },
        secondsLabels: {
            type: Array,
            default: function () {
                return ['seconds', 'second'];
            }
        },
        inLabel: {
            type: String,
            default: 'in'
        },
        endEvent: {
            type: String,
            default: 'discard'
        }
    },

    data: function () {
        return {
            expiration: null,
            label: this.defaultLabel,
            timer: null
        }
    },

    methods: {
        remaining: function () {
            const remainingSeconds = (this.expiration - new Date())/1000;

            let bag = []

            if (remainingSeconds < 0) {
                this.label = null;
                clearInterval(this.timer);
                this.$parent.$emit(this.endEvent);
                return;
            }

            let interval = Math.floor(remainingSeconds / 3600);
            if (interval > 0) {
                bag.push(interval);
                if (interval === 1) {
                    bag.push(this.hoursLabels[1]);
                }

                if (interval > 1) {
                    bag.push(this.hoursLabels[0]);
                }
            }

            interval = Math.floor((remainingSeconds % 3600) / 60);
            if (interval > 0) {
                bag.push(interval);
                if (interval === 1) {
                    bag.push(this.minutesLabels[1]);
                }

                if (interval > 1) {
                    bag.push(this.minutesLabels[0]);
                }
            }

            interval = Math.floor(remainingSeconds % 60);
            if (interval > 0) {
                bag.push(interval);
                if (interval === 1) {
                    bag.push(this.secondsLabels[1]);
                }

                if (interval > 1) {
                    bag.push(this.secondsLabels[0]);
                }
            }

            if (bag.length > 0) {
                bag.unshift(this.inLabel);
            }

            this.label = bag.join(' ');
        }
    },

    created: function () {
        this.expiration = new Date(this.expirationSeconds * 1000);

        this.timer = setInterval(() => {
            this.remaining();
        }, 1000);
    },

    template: `<span>{{ label }}</span>`
});
