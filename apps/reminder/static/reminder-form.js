Vue.component('reminder-form', {
    created: function () {
        this.$on('reminder:populate', this.populate);
    },

    data: function () {
        return {
            hours: null,
            minutes: null,
            message: null,
            comments: null,
            notificationId: null,
            url: null,
        }
    },

    methods: {
        populate(data) {
            this.hours = null;
            this.minutes = data.minutes;

            if (data.minutes > 60) {
                this.hours = Math.floor(data.minutes / 60)
                this.minutes = data.minutes % 60;
            }
            this.message = data.message;
            this.comments = data.comments;
            this.notificationId = data.notificationId;
            this.url = data.url;

            this.$nextTick(() => {
                this.$refs.reminderForm.submit();
            });
        }
    }
});
