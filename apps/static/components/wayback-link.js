Vue.component('wayback-link', {
    props: {
        defaultLabel: {
            type: String,
            required: false,
            default: 'cache'
        },

        url: {
            type: String,
            required: true
        }

    },

    data: function () {
        return {
            label: this.defaultLabel
        }
    },

    methods: {
        click: function (e) {
            this.label = 'checking...';

            fetch(this.url, {headers: {'Accept': 'application/json'}})
                .then(res => res.json())
                .then(data => {
                    if (data.url) {
                        this.label = 'found!';
                        setTimeout(() => window.location.href = data.url, 500);
                        return;
                    }

                    this.label = 'not available';
                })
                .catch(error => {
                    this.label = error.message;
                });

        }
    },
    template: `<a class="wayback" href="#" v-on:click.prevent="click">{{ label }}</a>`
})