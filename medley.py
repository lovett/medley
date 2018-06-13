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
import logging.config
import os
import os.path
import cherrypy
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

    cherrypy.config.update({
        "server_root": server_root,

        # Jinja templating won't work unless tools.encode is off
        "tools.encode.on": False,

        # Gzipping locally avoids Etag complexity. If a reverse
        # proxy handles it, the Etag could be dropped.
        "tools.gzip.on": True
    })

    # Configuration
    #
    # Application configuration is loaded from /etc/medley.conf or
    # medley.conf in the application root, whichever is found first.
    config_candidates = (
        "/etc/medley.conf",
        os.path.join(server_root, "medley.conf")
    )

    try:
        config = next(
            (candidate for candidate in config_candidates
             if os.path.isfile(candidate)),
        )
    except StopIteration:
        raise SystemExit("No configuration file")

    cherrypy.config.update(config)

    # Derived configuration
    #
    # Some configuration values are set automatically.
    cherrypy.config.update({
        "app_root": app_root
    })

    # Directory creation
    #
    # Filesystem paths declared by the config are expected to exist.
    for key in ("database_dir", "cache_dir", "log_dir"):
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
        # its static path is not under its app path.
        app_path = "/{}".format(app)
        static_url = "/static"
        if app == "homepage":
            app_path = "/"
            static_url = "/homepage/static"

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

    # Attempt to drop privileges if daemonized
    if cherrypy.config.get("server.daemonize"):
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

        pid_file = cherrypy.config.get("server.pid")
        if pid_file:
            cherrypy.process.plugins.PIDFile(
                cherrypy.engine,
                pid_file
            ).subscribe()

    # Plugins
    plugins.applog.Plugin(cherrypy.engine).subscribe()
    plugins.scheduler.Plugin(cherrypy.engine).subscribe()

    plugins.asterisk.Plugin(cherrypy.engine).subscribe()
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
    cherrypy.tools.response_time = tools.response_time.Tool()
    cherrypy.tools.negotiable = tools.negotiable.Tool()
    cherrypy.tools.template = tools.template.Tool()
    cherrypy.tools.capture = tools.capture.Tool()

    # Logging
    error_log_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(
            cherrypy.config.get("log_dir"),
            "error.log"
        ),
        when="D",
        interval=1,
        backupCount=14,
        encoding="utf8"
    )
    error_log_handler.setLevel(logging.INFO)

    # pylint: disable=protected-access
    error_log_handler.setFormatter(cherrypy._cplogging.logfmt)

    cherrypy.log.error_log.addHandler(error_log_handler)

    access_log_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(
            cherrypy.config.get("log_dir"),
            "access.log"
        ),
        when="D",
        interval=1,
        backupCount=14,
        encoding="utf8"
    )
    access_log_handler.setLevel(logging.INFO)

    # pylint: disable=protected-access
    access_log_handler.setFormatter(cherrypy._cplogging.logfmt)

    cherrypy.log.access_log.addHandler(access_log_handler)

    cherrypy.engine.start()
    cherrypy.engine.publish("logindex:parse")

    cherrypy.engine.block()


if __name__ == '__main__':
    main()
