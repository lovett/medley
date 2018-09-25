Vue.component('shortcut-link', {
    created: function () {
        window.addEventListener('keyup', this.keyup)
    },

    props: {
        index: {
            type: Number,
            required: true
        },

        label: {
            type: String,
            default: null
        },

        url: {
            type: String,
            required: true
        },
    },

    data: function () {
        return {
            linkText: this.label || this.url
        }
    },

    methods: {
        keyup: function (e) {
            if (parseInt(e.key, 10) === this.index) {
                window.location.href = this.url;
            }
        }
    },

    template: `
        <a class="shortcut-link" v-bind:href="this.url" v-on:keyup="keyup">
            <span>{{ this.index }}</span>
            {{ linkText }}
        </a>
    `
})
