Vue.component('bounce-form', {
    props: {
        endpoint: {
            type: String,
            required: true,
        }
    },

    data: function () {
        return {
            site: '',
            name: '',
            group: ''
        }
    },

    methods: {
        submit: function (e) {
            let destination = `${window.location.pathname}?group=${this.group}`;

            fetch(this.endpoint, {
                method: 'PUT',
                headers: {
                    'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
                },
                body: `site=${this.site}&name=${this.name}&group=${this.group}`
            }).then(function (res) {
                if (res.status === 204) {
                    window.location.href = destination;
                } else {
                    alert(res.status);
                }
            });
        }
    }
});
