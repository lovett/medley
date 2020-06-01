# Medley

A collection of small, single-purpose web applications that share
services but are otherwise independent.

Medley is build on the CherryPy framework.

## Setup

Medley targets the current version of Python 3 in Raspbian, currently
3.7. Setup is driven by `make`.

```sh
# Create a Python virtual environment
make venv
source venv/bin/activate

# Install third-party libraries
make setup

# Start the server on localhost:8085
make serve
```

## Configuration

The server's default configuration is reasonable for production use.
Adjustments to the defaults can be made with environment
variables. Any environment variable that starts with `MEDLEY__` will be
added to the CherryPy global config. This convention is for
compatibility with systemd.

`MEDLEY__database_dir`: The filesystem path to the directory that
should be used for Sqlite databases. Default: `./db`

`MEDLEY__engine__autoreload__on`: Whether the CherryPy server should watch
for changes to application files and restart itself. Only useful during
development. Default: `False`

`MEDLEY__local_maintenance`: Whether the server should allow requests
from localhost that perform cleanup and maintenance operations. These
can be time intensive and block other requests, and are meant to run
when the application isn't busy. Default: `True`

`MEDLEY__log__screen`: Whether log messages should be written to the
server's stdout. Default: `True`

`MEDLEY__log__screen_access`: If `MEDLEY__log__screen` is enabled,
whether access logs should also be written to stdout. Default: `False`

`MEDLEY__memorize_hashes`: Whether the server should keep static asset
file hashes in memory for use with HTTP cache control. Useful in
production but not in development. Default: `True`

`MEDLEY__request__show_tracebacks`: Whether CherryPy should display
Python error trackebacks in the browser. Default: `False`

`MEDLEY__server__daemonize`: Whether the CherryPy server should run as
a daemon. Unnecessary when the server is being manged by
`systemd`. Default: `False`

`MEDLEY__server__socket_host`: The IP the server should listen
on. Default: `127.0.0.1`

`MEDLEY__server__socket_port`: The port the server should listen
on. Default: `8085`

`MEDLEY__tools__gzip__on`: Whether to enable gzip
compression. Default: `True`

## Acknowledgements

This project gratefully makes use of other open-source projects:

* [CherryPy](https://cherrypy.org/)
* [flag-icon-css](http://flag-icon-css.lip.is/)
* [Sqlite](https://sqlite.org/)
* [Vue.js](https://vuejs.org/)
* [Feather icons](https://feathericons.com)
