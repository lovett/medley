# Medley

A collection of small, single-purpose web applications that live under
one roof. It's for odds-and-ends situations where you think to
yourself, "I should write a script/app/api for that..." but
don't want it to turn into a full-blown project.

Medley is written in Python and uses the CherryPy framework with
SQLite.

You probably don't want to run this application yourself. It's
entirely driven by whatever I have a need for, so unless you're me the
roster of what's available will seem random.

It might be relevant if you're building something of your own with
CherryPy and are interested in how the pieces of that framework can be
put together.

## Setup

I target the current version of Python 3 in Raspbian, currently
3.7. Everything else should be standard Python application ceremony,
driven by `make`:

```sh
# Create a virtual environment
make venv
source venv/bin/activate

# Install third-party libraries
make setup

# Start a dev server on localhost:8085
make serve
```

## Configuration

The server's default configuration is reasonable for production use.
Adjustments to the defaults can be made with environment
variables. Any environment variable that starts with `MEDLEY__` will be
added to the CherryPy global config.

For compatibility with systemd, double underscores are used in place
of periods in environment variable names.

`MEDLEY__database_dir`: The filesystem path to the directory that
should be used for Sqlite databases. Default: `./db`

`MEDLEY__engine__autoreload__on`: Whether the CherryPy webserver should watch
for changes to application files and restart itself. Only useful in
development. Default: `False`

`MEDLEY__local_maintenance`: Whether the server should allow requests
from localhost that perform cleanup and maintenance operations. These
can be time intensive and block other requests, and are meant to run
when the application isn't busy. Default: `True`

`MEDLEY__log__screen`: Whether log messages should be written to the stdout of the
tty running the server process. Default: `True`

`MEDLEY__log__screen_access`: Whether access logs should be written to stdout
when `log.screen` is enabled. Default: `False`

`MEDLEY__memorize_hashes`: Whether the server should keep static asset file
hashes in memory for use with HTTP cache control. Useful in production
but counterproductive in development. Default: `True`

`MEDLEY__request__show_tracebacks`: Whether CherryPy should display Python
trackebacks in the browser when errors occur. Default: `False`

`MEDLEY__server__daemonize`: Whether the CherryPy server should run as
a daemon. Not necessary when the server is being manged by
`systemd`. Default: `False`

`MEDLEY__server__socket_host`: The IP the server should listen on. Default:
`127.0.0.1`

`MEDLEY__server__socket_port`: The port the server should listen
on. Default: `8085`

`MEDLEY__tools__gzip__on`: Whether to enable gzip compression. Default: `True`

## Acknowledgements

This project gratefully makes use of other open-source projects,
including but not limited to:

* [CherryPy](https://cherrypy.org/)
* [flag-icon-css](http://flag-icon-css.lip.is/)
* [Pendulum](https://pendulum.eustace.io)
* [Sqlite](https://sqlite.org/)
* [Vue.js](https://vuejs.org/)
