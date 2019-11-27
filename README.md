# Medley

A collection of small, single-purpose web applications that live under
one roof so that each one doesn't have to reinvent all the wheels.

It's for all the situations when you think to yourself, "I should
write a script/app/webpage that does X" but then get waylaid by
setting up Y, Z, and all the other things that need to be established
before X is even on the table.

It's also driven by whatever I have a need for, so unless you're me
the roster of what's available will seem random. Because it is.

There currently around two dozen applications and services. Some of
the more interesting ones include:

* a bookmark manager
* a text-to-speech service that uses Microsoft's Speech API
* a URL bouncer for jumping between dev, stage, and production
  versions of a given URL
* a webserver log file parser, archiver, and viewer
* an alarm and reminder service

Medley is written in Python 3 and uses the CherryPy framework with
SQLite.

## Setup
You'll need at least Python 3.5. The rest should just be standard
Python application ceremony:

```sh
# Set up a virtual environment
make venv
source venv/bin/activate

# Install third-party libraries
make setup

# Optional: install one additional library for audio playback.
make setup-audio

# Start the server
make serve
```

## Configuration
By default the server runs under a development configuration and
listens on port 8085. The following default values can be overridden
by creating a file named `medley.conf` in either the application root,
or under `/etc`.

If used, the `medley.conf` file should be formatted in INI style with
all values placed under a section called "global". For example:

```ini
[global]
database_dir: "/var/db"
engine.autoreload.on: False
...
```

**cache_dir**: The path to the directory that should be used for
filesystem caching. Default: `./cache`

**database_dir**: The path to the directory that should be used for
Sqlite databases. Default: `./db`

**engine.autoreload.on**: Whether the CherryPy webserver should watch
for changes to application files and restart itself. Only useful in
development. Default: `False`

**local_maintenance**: Whether the server should allow requests
from localhost that perform cleanup and maintenance operations. These
can be time intensive and block other requests, and are meant to run
when the application is otherwise dormant. Default: `True`

**log.screen**: Whether requests should be written to the stdout of the
tty running the server process. Default: `True`

**log.screen_access**: Whether access logs should be written to stdout
when screen logging is enabled. Default: `False`

**memorize_checksums**: Whether the server should keep static asset file
hashes in memory for use with HTTP cache control. Useful in production
but counterproductive in development. Default: `True`

**request.show_tracebacks**: Whether CherryPy should display Python
trackebacks when errors occur. Default: `False`

**server.daemonize**: Whether the CherryPy server should run as a
daemon. Not meaningful in production unless systemd is not being
used. Default: `False`

**server.socket_host**: The IP the server should listen on. Default:
`127.0.0.1`

**server.socket_port**: The port the server should listen on. Default:
`8085`

**tools.gzip.on**: Whether to enable gzip compression. Default: `True`

## Acknowledgements

This project gratefully makes use of other open-source projects,
including but not limited to:

* [CherryPy](https://cherrypy.org/)
* [flag-icon-css](http://flag-icon-css.lip.is/)
* [Vue.js](https://vuejs.org/)
