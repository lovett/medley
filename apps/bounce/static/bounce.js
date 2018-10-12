Vue.component('bounce-form', {
    data: function () {
        return  {
            errorMessage: null,
            successMessage: null
        }
    },

    props: {
        endpoint: {
            type: String,
            required: true,
        },
        site: {
            type: String
        },
        name: {
            type: String
        },
        group: {
            type: String
        },
        url: {
            type: String
        }
    },

    methods: {
        submit: function (e) {
            fetch(this.endpoint, {
                method: 'PUT',
                headers: {
                    'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
                },
                body: `site=${this.site}&name=${this.name}&group=${this.group}`
            }).then((res) => {
                if (res.status === 204) {
                    this.errorMessage = null;
                    this.successMessage = 'Success!';
                    const destination = `${window.location.pathname}?u=${encodeURIComponent(this.url)}`;
                    setTimeout(() => {
                        window.location.href = destination;
                    }, 500);
                } else {
                    this.successMessage = null;
                    this.errorMessage = res.statusText;
                }
            });
        }
    }
});
