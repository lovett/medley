Vue.component('reminder-template', {
    created: function () {
        this.$on('discarded', this.hide);
    },

    data: function () {
        return {
            visible: true
        }
    },

    props: {
        uid: {
            type: String,
            required: true
        },
        message: {
            type: String,
            required: true
        },
        minutes: {
            type: Number,
            required: true
        },
        comments: {
            type: String,
            required: false
        },
        notificationId: {
            type: String,
            required: false
        },
        url: {
            type: String,
            required: false
        }
    },

    methods: {
        hide: function () {
            this.visible = false;
        },
        apply: function (e) {
            this.$parent.$emit('reminder:populate', this.$props);
        }
    }
});
