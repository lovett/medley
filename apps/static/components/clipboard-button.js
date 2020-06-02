Vue.component('clipboard-button', {
    props: {
        label: {
            type: String,
            required: false
        },

        targetValue: {
            type: String,
            required: false,
            default: undefined
        },

        targetId: {
            type: String,
            required: false,
            default: undefined
        },

        tooltip: {
            type: String,
            required: false,
            default: 'Copy to clipboard'
        }

    },

    data: function () {
        let copyTarget = this.targetValue;
        if (this.targetId) {
            copyTarget = document.getElementById(this.targetId).textContent;
        }

        return {
            clicked: false,
            copyTarget: copyTarget
        }
    },


    methods: {
        click: function (e) {
            this.$refs.surrogate.select();
            document.execCommand('copy');
            this.clicked = true;
            setTimeout(() => this.clicked = false, 1000);
        }
    },

    template: `
    <div class="action-button clipboard-button">
        <a href="#" v-on:click.prevent="click" v-bind:class="{ clicked: clicked }" v-bind:title="tooltip">
            <svg class="icon"><use xlink:href="#icon-copy"></use></svg>
       </a>
       <span class="label">{{ this.label }}</span>
       <form>
           <textarea ref="surrogate">{{ this.copyTarget }}</textarea>
       </form>
    </div>
    `
})