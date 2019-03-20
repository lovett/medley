Vue.component('discardable-record', {

    created: function () {
        this.$on('discard', this.discard);
    },

    data: function() {
        return {
            styles: {}
        }
    },

    methods: {
        discard: function () {
            this.$el.hidden = true;
            fetch(this.url, {
                method: this.method
            }).then(res => {
                if (res.ok) {
                    this.$parent.$emit('discarded');
                }
            }).catch(err => {
                this.$el.hidden = false;
            });
        }
    },

    props: {
        // The HTTP method to invoke the URL with.
        method: {
            type: String,
            required: false,
            default: 'DELETE'
        },

        // The remote endpoint to call.
        url: {
            type: String,
            required: true
        }
    }

})
