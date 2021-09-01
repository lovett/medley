"""Medley, a collection of web-based utilities

Medley is an application server for lightweight, single-purpose
applications that are too small or trivial to bother making
standalone.

Having them under one roof provides makes it possible to share
frequently-needed services instead of starting from zero. It also
helps each application stay relatively small.
"""

import argparse
import importlib
import logging
import os
import os.path
import sys
import typing
import zipfile
import cherrypy
import portend
import sdnotify
import plugins.applog
import plugins.assets
import plugins.audio
import plugins.bookmarks
import plugins.cache
import plugins.capture
import plugins.cdr
import plugins.clock
import plugins.converters
import plugins.decorators
import plugins.filesystem
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
import plugins.metrics
import plugins.mixins
import plugins.notifier
import plugins.recipes
import plugins.registry
import plugins.scheduler
import plugins.speak
import plugins.urlfetch
import plugins.url
import plugins.weather
import tools.capture
import tools.etag
import tools.whitespace
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
        "cache_static_assets": True,
        "database_dir": "./db",
        "etags": True,
        "engine.autoreload.on": False,
        "local_maintenance": True,
        "log.screen": True,
        "log.screen_access": False,
        "log.access_file": "",
        "log.error_file": "",
        "memorize_hashes": True,
        "prefetch": True,
        "request.show_tracebacks": False,
        "server.daemonize": False,
        "server.socket_host": "127.0.0.1",
        "server.socket_port": 8085,
        "server_root": server_root,
        "tools.encode.on": False,

        # Gzipping locally avoids Etag complexity. If a reverse
        # proxy handles it, the Etag could be dropped.
        "tools.gzip.on": True,

        "zipapp": not os.path.isdir(server_root)
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
    except PermissionError as err:
        raise SystemExit("Permission error on database directory") from err

    # Tools
    cherrypy.tools.capture = tools.capture.Tool()
    cherrypy.tools.etag = tools.etag.Tool()
    cherrypy.tools.whitespace = tools.whitespace.Tool()
    cherrypy.tools.provides = tools.provides.Tool()

    # Mount the apps
    if cherrypy.config["zipapp"]:
        with zipfile.ZipFile(server_root) as archive:
            apps = [
                name.split("/")[1]
                for name in archive.namelist()
                if name.endswith("main.py")
            ]
    else:
        apps = [
            entry.name
            for entry in os.scandir(app_root)
            if entry.name.isalpha()
        ]

    for app in apps:
        app_path = f"/{app}"
        if app == "homepage":
            app_path = "/"

        main = importlib.import_module(f"apps.{app}.main")

        cherrypy.tree.mount(
            main.Controller(),  # type: ignore
            app_path,
            {
                "/": {
                    "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
                    "tools.whitespace.on": True
                },
            }
        )

    # Plugins
    plugins.applog.Plugin(cherrypy.engine).subscribe()
    plugins.assets.Plugin(cherrypy.engine).subscribe()
    plugins.audio.Plugin(cherrypy.engine).subscribe()
    plugins.bookmarks.Plugin(cherrypy.engine).subscribe()
    plugins.cache.Plugin(cherrypy.engine).subscribe()
    plugins.capture.Plugin(cherrypy.engine).subscribe()
    plugins.cdr.Plugin(cherrypy.engine).subscribe()
    plugins.clock.Plugin(cherrypy.engine).subscribe()
    plugins.converters.Plugin(cherrypy.engine).subscribe()
    plugins.filesystem.Plugin(cherrypy.engine).subscribe()
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
    plugins.metrics.Plugin(cherrypy.engine).subscribe()
    plugins.notifier.Plugin(cherrypy.engine).subscribe()
    plugins.recipes.Plugin(cherrypy.engine).subscribe()
    plugins.registry.Plugin(cherrypy.engine).subscribe()
    plugins.speak.Plugin(cherrypy.engine).subscribe()
    plugins.url.Plugin(cherrypy.engine).subscribe()
    plugins.urlfetch.Plugin(cherrypy.engine).subscribe()
    plugins.weather.Plugin(cherrypy.engine).subscribe()

    # Skip unnecessary services when running in serverless mode.
    #
    # This includes Medley's scheduler plugin and CherryPy's HTTP
    # server.
    if cherrypy.config.get("serverless"):
        cherrypy.server.unsubscribe()
        cherrypy.engine.start()
        return

    plugins.scheduler.Plugin(cherrypy.engine).subscribe()

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

    # See if the configured port is in use
    #
    # If it is, let the OS pick an alternative so that server startup
    # is more resilient. Cherrypy performs similar checking during
    # engine start, but it's unclear how to catch that exception
    # from here.
    try:
        portend.Checker().assert_free(
            cherrypy.config.get("server.socket_host"),
            cherrypy.config.get("server.socket_port")
        )
    except portend.PortNotFree:
        port = int(cherrypy.config.get("server.socket_port"))
        cherrypy.engine.log(
            (f"Port {port} is not available, "
             "will leave it to the OS to assign one."),
            level=40
        )
        cherrypy.config.update({
            "server.socket_port": 0
        })

    cherrypy.engine.start()


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()

    argparser.add_argument(
        "--publish",
        help='publish static assets',
        action="store_true"
    )

    argparser.set_defaults(publish=False)
    args = argparser.parse_args()

    cherrypy.config.update({"serverless": args.publish})

    setup()

    if args.publish:
        cherrypy.engine.publish(
            "assets:publish",
            reset=True
        )
        cherrypy.engine.exit()
        sys.exit()

    if cherrypy.config.get("notify_systemd_at_startup"):
        sdnotify.SystemdNotifier().notify("READY=1")

    cherrypy.engine.publish("assets:publish")
    cherrypy.engine.publish("server:ready")
    cherrypy.engine.block()
