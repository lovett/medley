Vue.component('discard-button', {
    props: {
        svgSymbol: {
            type: String,
            required: false,
            default: "#delete"
        },

        emitEvent: {
            type: String,
            required: false,
            default: 'discard'
        },
        tooltip: {
            type: String,
            required: false,
            default: ''
        }
    },
    methods: {
        click: function (e) {
            this.$parent.$emit(this.emitEvent);
        }
    },
    template: `<a href="#" v-on:click="click" v-bind:title="tooltip"><svg class="icon"><use v-bind:xlink:href="svgSymbol"></use></svg></a>`,
})
