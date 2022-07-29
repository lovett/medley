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
import cherrypy
import portend
import sdnotify
from typing_extensions import TypedDict
import plugins.applog
import plugins.app_url
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
import plugins.foodlog
import plugins.gcp_appengine
import plugins.gcp_storage
import plugins.geography
import plugins.hasher
import plugins.input
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
import plugins.weather
import plugins.warehouse
import tools.capture
import tools.etag
import tools.whitespace
import tools.provides

# Type definitions for server configuration.
#
# This is similar to CherryPy's configuration, but more flat.
# It also dictates what can be overriden by environment variables.
ServerConfig = TypedDict("ServerConfig", {
    "access_log": str,
    "autoreload": bool,
    "daemonize": bool,
    "database_dir": str,
    "encode": bool,
    "error_log": str,
    "etags": bool,
    "gzip": bool,
    "log_screen": bool,
    "log_screen_access": bool,
    "memorize_hashes": bool,
    "notify_systemd": bool,
    "prefetch": bool,
    "server_host": str,
    "server_port": int,
    "server_root": str,
    "tracebacks": bool,
})

# The parts of CherryPy's configuration that use dot notation. Mapping
# the shorter names in the server config to these longer equivalents makes
# it easeier to use environment variable overrides.
ServerConfigAliases = TypedDict("ServerConfigAliases", {
    "engine.autoreload.on": bool,
    "log.access_file": str,
    "log.error_file": str,
    "log.screen": bool,
    "log.screen_access": bool,
    "request.show_tracebacks": bool,
    "server.daemonize": bool,
    "server.socket_host": str,
    "server.socket_port": int,
    "tools.encode.on": bool,
    "tools.gzip.on": bool,
})


def env_boolean(key: str, default: bool) -> bool:
    """Read a server environment variable as a boolean."""
    value = os.getenv(f"MEDLEY_{key}")
    if value == "True":
        return True
    if value == "False":
        return False
    return default


def env_integer(key: str, default: int) -> int:
    """Read a server environment variable as an integer."""
    value = os.getenv(f"MEDLEY_{key}")
    if value:
        return int(value)
    return default


def env_string(key: str, default: str) -> str:
    """Read a server environment variable."""
    return os.getenv(f"MEDLEY_{key}", default)


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
    config = ServerConfig(
        access_log=env_string("access_log", ""),
        autoreload=env_boolean("autoreload", False),
        daemonize=env_boolean("daemonize", False),
        database_dir=env_string("database_dir", "./db"),
        encode=env_boolean("encode", False),
        error_log=env_string("error_log", ""),
        etags=env_boolean("etags", True),
        gzip=env_boolean("gzip", True),
        log_screen=env_boolean("log_screen", True),
        log_screen_access=env_boolean("log_screen_access", False),
        memorize_hashes=env_boolean("memorize_hashes", True),
        notify_systemd=env_boolean("notify_systemd", False),
        prefetch=env_boolean("prefetch", True),
        server_host=env_string("server_host", "127.0.0.1"),
        server_port=env_integer("server_port", 8085),
        server_root=server_root,
        tracebacks=env_boolean("tracebacks", False),
    )

    cherrypy.config.update(config)

    # Remap medley configuration to cherrypy configuration.
    aliases = {
        "engine.autoreload.on": config["autoreload"],
        "log.access_file": config["access_log"],
        "log.error_file": config["error_log"],
        "log.screen": config["log_screen"],
        "log.screen_access": config["log_screen_access"],
        "request.show_tracebacks": config["tracebacks"],
        "server.daemonize": config["daemonize"],
        "server.socket_host": config["server_host"],
        "server.socket_port": config["server_port"],
        "tools.encode.on": config["encode"],
        "tools.gzip.on": config["gzip"],
    }  # type: ServerConfigAliases

    cherrypy.config.update(aliases)

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
    apps = [
        entry.name
        for entry in os.scandir(app_root)
        if entry.name.isalpha()
    ]

    for app in apps:
        # Must not end in a slash. For the root, must be an empty
        # string rather than "/"
        app_path = f"/{app}"
        if app == "homepage":
            app_path = ""

        app_main = importlib.import_module(f"apps.{app}.main")

        cherrypy.tree.mount(
            app_main.Controller(),  # type: ignore
            app_path,
            {
                "/": {
                    "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
                    "tools.whitespace.on": True,
                },
            }
        )

    # Plugins
    plugins.applog.Plugin(cherrypy.engine).subscribe()
    plugins.app_url.Plugin(cherrypy.engine).subscribe()
    plugins.assets.Plugin(cherrypy.engine).subscribe()
    plugins.audio.Plugin(cherrypy.engine).subscribe()
    plugins.bookmarks.Plugin(cherrypy.engine).subscribe()
    plugins.cache.Plugin(cherrypy.engine).subscribe()
    plugins.capture.Plugin(cherrypy.engine).subscribe()
    plugins.cdr.Plugin(cherrypy.engine).subscribe()
    plugins.clock.Plugin(cherrypy.engine).subscribe()
    plugins.converters.Plugin(cherrypy.engine).subscribe()
    plugins.filesystem.Plugin(cherrypy.engine).subscribe()
    plugins.foodlog.Plugin(cherrypy.engine).subscribe()
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
    plugins.urlfetch.Plugin(cherrypy.engine).subscribe()
    plugins.weather.Plugin(cherrypy.engine).subscribe()
    plugins.warehouse.Plugin(cherrypy.engine).subscribe()

    # Skip unnecessary services when running in serverless mode.
    #
    # This includes Medley's scheduler plugin and CherryPy's HTTP
    # server.
    if cherrypy.config.get("serverless"):
        cherrypy.server.unsubscribe()
        cherrypy.engine.start()
        return

    plugins.input.Plugin(cherrypy.engine).subscribe()
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
            config["server_host"],
            config["server_port"],
        )
    except portend.PortNotFree:
        cherrypy.engine.log(
            f"Port {config['server_port']} is not available",
            level=40
        )
        cherrypy.config.update({
            "server.socket_port": 0
        })

    cherrypy.engine.start()


def main() -> None:
    """The entry point for the application."""
    argparser = argparse.ArgumentParser()

    argparser.add_argument(
        "--lintcheck",
        help="determine if a file should be linted"
    )

    argparser.add_argument(
        "--lintpass",
        help="mark a file as successfully linted"
    )

    args = argparser.parse_args()

    if args.lintpass:
        hasher = plugins.hasher.Plugin(cherrypy.engine)
        current_hash = hasher.hash_value(args.lintpass)

        plugins.cache.Plugin(cherrypy.engine).set(
            f"lintcheck:{args.lintpass}",
            current_hash,
            86400 * 365
        )
        sys.exit()

    if args.lintcheck:
        hasher = plugins.hasher.Plugin(cherrypy.engine)
        cache = plugins.cache.Plugin(cherrypy.engine)
        current_hash = hasher.hash_value(args.lintcheck)
        stored_hash = cache.get(f"lintcheck:{args.lintcheck}")

        if current_hash != stored_hash:
            print("yes")
        else:
            print("no")
        sys.exit()

    setup()

    if cherrypy.config.get("notify_systemd"):
        sdnotify.SystemdNotifier().notify("READY=1")

    cherrypy.engine.publish("assets:publish")
    cherrypy.engine.publish("server:ready")
    cherrypy.engine.block()


if __name__ == '__main__':
    main()
