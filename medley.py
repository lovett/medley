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
import cherrypy
import sdnotify
import plugins
import tools


# pylint: disable=too-many-statements
def main():
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
        "cache_dir": "./cache",
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
        "tools.conditional_auth.on": False,
        "users": {},
        "tools.conditional_auth.whitelist": "",

        # Jinja templating won't work unless tools.encode is off
        "tools.encode.on": False,

        # Gzipping locally avoids Etag complexity. If a reverse
        # proxy handles it, the Etag could be dropped.
        "tools.gzip.on": True,
    })

    # Overrides to the default configuration are sourced from
    # one or more external files.
    config_candidates = (
        "/etc/medley.conf",
        os.path.join(server_root, "medley.conf")
    )

    for path in config_candidates:
        if os.path.isfile(path):
            cherrypy.config.update(path)
            cherrypy.log("Configuration overrides loaded from {}".format(
                path
            ))

    # Directory creation
    #
    # Filesystem paths specified in the configuration are expected to
    # already exist. Try to create them if they don't.
    for key in ("database_dir", "cache_dir"):
        value = cherrypy.config.get(key)

        try:
            os.mkdir(value)
        except FileExistsError:
            pass
        except PermissionError:
            raise SystemExit(
                "Unable to create {} directory at {}".format(key, value)
            )

    # Mount the apps
    for app in os.listdir(app_root):

        if not os.path.isfile(os.path.join(app_root, app, "main.py")):
            continue

        app_module = importlib.import_module("apps.{}.main".format(app))

        # Treat all controllers as exposed by default.
        # This is a Cherrypy-ism.
        if not hasattr(app_module.Controller, "exposed"):
            app_module.Controller.exposed = True

        # Treat all controllers as user-facing by default. This is a
        # Medley-ism. Service apps should override this attribute
        # locally.
        if not hasattr(app_module.Controller, "user_facing"):
            app_module.Controller.user_facing = True

        app_config = {
            "/": {
                "request.dispatch": cherrypy.dispatch.MethodDispatcher()
            },
        }

        # The homepage app is unique. Its app name is not its url, and
        # its static path is not under its app path. It also has additional
        # configuration for serving the favicon.
        app_path = "/{}".format(app)
        static_url = "/static"
        if app == "homepage":
            app_path = "/"
            static_url = "/homepage/static"

            app_config["/favicon.ico"] = {
                "tools.staticfile.on": True,
                "tools.staticfile.filename": os.path.realpath(
                    "./apps/shared/static/favicon/favicon.ico"
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
                "tools.expires.on": True,
                "tools.expires.secs": 86400 * 7
            }

        cherrypy.tree.mount(
            app_module.Controller(),
            app_path,
            app_config
        )

    # Plugins
    plugins.applog.Plugin(cherrypy.engine).subscribe()
    plugins.scheduler.Plugin(cherrypy.engine).subscribe()

    plugins.audio.Plugin(cherrypy.engine).subscribe()
    plugins.bookmarks.Plugin(cherrypy.engine).subscribe()
    plugins.cache.Plugin(cherrypy.engine).subscribe()
    plugins.capture.Plugin(cherrypy.engine).subscribe()
    plugins.cdr.Plugin(cherrypy.engine).subscribe()
    plugins.checksum.Plugin(cherrypy.engine).subscribe()
    plugins.converters.Plugin(cherrypy.engine).subscribe()
    plugins.formatting.Plugin(cherrypy.engine).subscribe()
    plugins.geography.Plugin(cherrypy.engine).subscribe()
    plugins.hasher.Plugin(cherrypy.engine).subscribe()
    plugins.ip.Plugin(cherrypy.engine).subscribe()
    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    plugins.logindex.Plugin(cherrypy.engine).subscribe()
    plugins.maintenance.Plugin(cherrypy.engine).subscribe()
    plugins.markup.Plugin(cherrypy.engine).subscribe()
    plugins.notifier.Plugin(cherrypy.engine).subscribe()
    plugins.parse.Plugin(cherrypy.engine).subscribe()
    plugins.registry.Plugin(cherrypy.engine).subscribe()
    plugins.speak.Plugin(cherrypy.engine).subscribe()
    plugins.memorize.Plugin(cherrypy.engine).subscribe()
    plugins.urlfetch.Plugin(cherrypy.engine).subscribe()
    plugins.url.Plugin(cherrypy.engine).subscribe()

    # Tools
    cherrypy.tools.conditional_auth = tools.conditional_auth.Tool()
    cherrypy.tools.negotiable = tools.negotiable.Tool()
    cherrypy.tools.capture = tools.capture.Tool()

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
    cherrypy.engine.publish("scheduler:revive")
    cherrypy.engine.publish("logindex:parse")
    cherrypy.engine.publish("bookmarks:add:fulltext")

    if os.environ.get("MEDLEY_NOTIFY_STARTUP"):
        systemd_notifier = sdnotify.SystemdNotifier()
        systemd_notifier.notify("READY=1")

    cherrypy.engine.block()


if __name__ == '__main__':
    main()
