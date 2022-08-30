# Medley

A collection of small web applications.

## Development Setup

Medley is written in Python and targets version 3.10. Setup is driven by `make`.

```sh
# Create a virtual environment
make venv

# Install third-party libraries
make setup

# Start the server on localhost:8085
make serve
```

## SELinux Configuration

```sh
sudo semanage port -a -t http_port_t -p tcp 8085
setsebool -P httpd_can_network_relay 1
```

## Application Configuration

Medley's default configuration can be adjusted through environment
variables.

`MEDLEY_access_log`: The file path for site-wide request
logging. Default: Not set

`MEDLEY_autoreload`: Whether the server should watch for changes to
application files and restart itself. Only useful during
development. Default: `False`

`MEDLEY_daemonize`: Whether the server should run as a daemon.
Unnecessary when the server is being manged by systemd and useful
during development. Default: `False`

`MEDLEY_database_dir`: The directory path for SQLite
databases. Default: `./db`

`MEDLEY_error_log`: The file path for site-wide error
logging. Unnecessary when the server is being managed by
systemd (use `journalctl` instead). Default: Not set

`MEDLEY_etags`: Whether to use `ETag` HTTP headers for caching.
Default: `True`

`MEDLEY_gzip`: Whether to enable gzip compression. Default: `True`

`MEDLEY_log_headers`: Whether error logging should include HTTP
request headers. Default: `False`

`MEDLEY_log_screen`: Whether log messages should be written to the
server's `stdout`. Default: `True`

`MEDLEY_log_screen_access`: Whether access logs should be written to
the `stdout` of the server process. Only applicable if
`MEDLEY_log_screen` is enabled. Default: `False`

`MEDLEY_memorize_hashes`: Whether the server should keep static asset
file hashes in memory for use with HTTP cache control. Useful in
production but not in development. Default: `True`

`MEDLEY_notify_systemd`: Whether the server should let systemd know it
has started and is ready to receive requests. Default: `False`

`MEDLEY_prefetch`: Whether the server is allowed to poll certain
external URLs on a recurring basis so that they can be served more
quickly from cache when needed. Default: `True`

`MEDLEY_server_host`: The IP the server should listen
on. Default: `127.0.0.1`

`MEDLEY_server_port`: The port the server should listen
on. Default: `8085`

`MEDLEY_tracebacks`: Whether CherryPy should display
Python error trackebacks in the browser. Default: `False`


## Acknowledgements

This project gratefully makes use of the following projects:

* [CherryPy](https://cherrypy.org/)
* [flag-icon-css](http://flag-icon-css.lip.is/)
* [SQLite](https://sqlite.org/)
* [Feather icons](https://feathericons.com)
