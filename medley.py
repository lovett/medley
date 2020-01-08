"""Medley, a collection of web-based utilities

Medley is an application server for lightweight, single-purpose
applications that are too small or trivial to bother making
standalone.

Having them under one roof provides makes it possible to share
frequently-needed services instead of starting from zero. It also
helps each application stay relatively small.
"""

import importlib
import logging
import os
import os.path
import typing
import cherrypy
import sdnotify
import plugins.applog
import plugins.audio
import plugins.bookmarks
import plugins.cache
import plugins.capture
import plugins.cdr
import plugins.checksum
import plugins.converters
import plugins.decorators
import plugins.formatting
import plugins.gcp_appengine
import plugins.gcp_storage
import plugins.geography
import plugins.hasher
import plugins.ip
import plugins.jinja
import plugins.logindex
import plugins.mail
import plugins.maintenance
import plugins.markup
import plugins.memorize
import plugins.mixins
import plugins.notifier
import plugins.parse
import plugins.registry
import plugins.scheduler
import plugins.speak
import plugins.urlfetch
import plugins.url
import tools.capture
import tools.etag
import tools.provides

# pylint: disable=too-many-statements
@plugins.decorators.log_runtime
def setup() -> None:
    """Configure and start the application server

    The application server is the backbone that individual
    applications are attached to. It does almost nothing by itself
    except load applications and plugins.
    """

    server_root = os.path.dirname(os.path.abspath(__file__))
    app_root = os.path.join(server_root, "apps")

    # Configuration defaults
    #
    # These are reasonable values for a production environment.
    cherrypy.config.update({
        "app_root": app_root,
        "cache_static_assets": True,
        "database_dir": "./db",
        "engine.autoreload.on": False,
        "local_maintenance": True,
        "log.screen": True,
        "log.screen_access": False,
        "log.access_file": "",
        "log.error_file": "",
        "memorize_checksums": True,
        "request.show_tracebacks": False,
        "server.daemonize": False,
        "server.socket_host": "127.0.0.1",
        "server.socket_port": 8085,
        "server_root": server_root,
        "tools.encode.on": False,
        "use_service_workers": True,

        # Gzipping locally avoids Etag complexity. If a reverse
        # proxy handles it, the Etag could be dropped.
        "tools.gzip.on": True,
    })

    # Configuration overrides
    #
    # Accept any environment variable that starts with "MEDLEY".
    # Double underscores are used for systemd compatibilty.
    environment_config: typing.Dict[str, typing.Any] = {
        key[8:].replace("__", "."): os.getenv(key)
        for key in os.environ
        if key.startswith("MEDLEY")
    }

    for key, value in environment_config.items():
        if value == "True":
            environment_config[key] = True
        if value == "False":
            environment_config[key] = False
        if value.isnumeric():
            environment_config[key] = int(value)

    if environment_config:
        cherrypy.config.update(environment_config)

    # Database Directory
    #
    # Databases will be created automatically, but the directory they
    # reside in needs to exist.
    try:
        os.mkdir(cherrypy.config.get("database_dir"))
    except FileExistsError:
        pass
    except PermissionError:
        raise SystemExit("No permission to create database directory")

    # Tools
    cherrypy.tools.capture = tools.capture.Tool()
    cherrypy.tools.etag = tools.etag.Tool()
    cherrypy.tools.provides = tools.provides.Tool()

    # Mount the apps
    for app in os.listdir(app_root):

        if not os.path.isfile(os.path.join(app_root, app, "main.py")):
            continue

        app_module = importlib.import_module(f"apps.{app}.main")

        app_config = {
            "/": {
                "request.dispatch": cherrypy.dispatch.MethodDispatcher()
            },
        }

        # The homepage app is unique. Its app name is not its url, and
        # its static path is not under its app path. It also has additional
        # configuration for serving the favicon and service worker.
        app_path = f"/{app}"
        static_url = "/static"
        if app == "homepage":
            app_path = "/"
            static_url = "/homepage/static"

            app_config["/favicon.ico"] = {
                "tools.staticfile.on": True,
                "tools.staticfile.filename": os.path.realpath(
                    "./apps/shared/static/favicon.ico"
                ),
            }

            app_config["/worker.js"] = {
                "tools.staticfile.on": True,
                "tools.staticfile.filename": os.path.realpath(
                    "./apps/shared/static/js/worker.js"
                ),
            }

        # An app can optionally have a dedicated directory for static assets
        static_path = os.path.join(app_root, app, "static")
        if os.path.isdir(static_path):

            app_config[static_url] = {
                "tools.gzip.on": True,
                "tools.gzip.mime_types": ["text/*", "application/*"],
                "tools.staticdir.on": True,
                "tools.staticdir.dir": os.path.realpath(static_path),
            }

            if cherrypy.config.get("cache_static_assets"):
                app_config[static_url].update({
                    "tools.expires.on": True,
                    "tools.expires.secs": 86400 * 7
                })

        cherrypy.tree.mount(
            app_module.Controller(),  # type: ignore
            app_path,
            app_config
        )

    # Plugins
    plugins.applog.Plugin(cherrypy.engine).subscribe()
    plugins.audio.Plugin(cherrypy.engine).subscribe()
    plugins.bookmarks.Plugin(cherrypy.engine).subscribe()
    plugins.cache.Plugin(cherrypy.engine).subscribe()
    plugins.capture.Plugin(cherrypy.engine).subscribe()
    plugins.cdr.Plugin(cherrypy.engine).subscribe()
    plugins.checksum.Plugin(cherrypy.engine).subscribe()
    plugins.converters.Plugin(cherrypy.engine).subscribe()
    plugins.formatting.Plugin(cherrypy.engine).subscribe()
    plugins.gcp_appengine.Plugin(cherrypy.engine).subscribe()
    plugins.gcp_storage.Plugin(cherrypy.engine).subscribe()
    plugins.geography.Plugin(cherrypy.engine).subscribe()
    plugins.hasher.Plugin(cherrypy.engine).subscribe()
    plugins.ip.Plugin(cherrypy.engine).subscribe()
    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    plugins.logindex.Plugin(cherrypy.engine).subscribe()
    plugins.maintenance.Plugin(cherrypy.engine).subscribe()
    plugins.markup.Plugin(cherrypy.engine).subscribe()
    plugins.memorize.Plugin(cherrypy.engine).subscribe()
    plugins.notifier.Plugin(cherrypy.engine).subscribe()
    plugins.parse.Plugin(cherrypy.engine).subscribe()
    plugins.registry.Plugin(cherrypy.engine).subscribe()
    plugins.scheduler.Plugin(cherrypy.engine).subscribe()
    plugins.speak.Plugin(cherrypy.engine).subscribe()
    plugins.url.Plugin(cherrypy.engine).subscribe()
    plugins.urlfetch.Plugin(cherrypy.engine).subscribe()

    # Disable access logging to the console
    #
    # This changes CherryPy's default behavior, which is to send
    # access and error logs to the screen when screen logging is
    # enabled. Turning off one but not the other only works when
    # logging to files.
    #
    # The log.screen_access config key is unique to this project.
    if not cherrypy.config.get("log.screen_access"):
        for handler in cherrypy.log.access_log.handlers:
            if isinstance(handler, logging.StreamHandler):
                cherrypy.log.access_log.handlers.remove(handler)

    cherrypy.engine.start()


if __name__ == '__main__':
    setup()

    if cherrypy.config.get("notify_systemd_at_startup"):
        sdnotify.SystemdNotifier().notify("READY=1")

    cherrypy.engine.publish("server:ready")
    cherrypy.engine.block()
