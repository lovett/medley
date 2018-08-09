Vue.component('new-item-button', {
    props: {
        label: {
            type: String,
            required: false
        },

        targetUrl: {
            type: String,
            required: true
        },

        tooltip: {
            type: String,
            required: false,
            default: 'New item'
        }

    },

    data: function () {
        return {
            clicked: false,
        }
    },


    methods: {
        click: function (e) {
            window.location.href = this.targetUrl;
        }
    },

    template: `
    <div class="action-button clipboard-button">
        <a href="#" v-on:click.prevent="click" v-bind:class="{ clicked: clicked }" v-bind:title="tooltip">
            <svg><use xlink:href="#new-item"></use></svg>
       </a>
       <span class="label">{{ this.label }}</span>
       <form>
           <textarea ref="surrogate">{{ this.copyTarget }}</textarea>
       </form>
    </div>
    `
})
