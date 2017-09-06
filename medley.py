"""Medley, a collection of web-based utilities.

Medley is a hub for miniature applications that each do one thing
reasonably well and might otherwise be one-off or throwaway scripts.

Putting them under a common roof means not having to start from zero
each time, and makes it easier to leverage existing things when build
new things.
"""

import importlib
import os
import os.path
import cherrypy
import plugins
import tools

def main():
    """Configure and start the medley server

    The server consists of the core application which displays a
    homepage of the available applications, as well as the set of
    those applications which are mounted as sub- or mini-applications.

    The core application is as minimal as possible so that
    applications can be modular and relatively independent of one
    another. However, certain applications provide models services to
    other applications. The independence of each application varies.

    """

    app_root = os.path.dirname(os.path.abspath(__file__))

    # Jinja templating won't work unless tools.encode is off
    cherrypy.config.update({
        "app_root": app_root,
        "tools.encode.on": False
    })

    # Load configuration from /etc/medley.conf if it exists, otherwise load
    # from the application root
    config_file = "/etc/medley.conf"
    if not os.path.isfile(config_file):
        config_file = os.path.join(app_root, "medley.conf")

    if not os.path.isfile(config_file):
        raise SystemExit("No configuration file")

    cherrypy.config.update(config_file)

    # Create required application directories
    for key in ("database_dir", "cache_dir", "log_dir"):
        value = cherrypy.config.get(key)
        try:
            os.mkdir(value)
        except PermissionError:
            raise SystemExit("Unable to create {} directory".format(key))
        except FileExistsError:
            pass

        if key == "log_dir":
            cherrypy.config.update({
                "log.access_file": os.path.join(value, "access.log"),
                "log.error_file": os.path.join(value, "error.log")
            })

    # Mount the apps
    app_dir = os.path.realpath("apps")

    for app in os.listdir(app_dir):
        main_path = os.path.join(app_dir, app, "main.py")

        if not os.path.isfile(main_path):
            continue

        app_module = importlib.import_module("apps.{}.main".format(app))

        try:
            url_path = app_module.Controller.URL
        except:
            continue

        app_config = {
            "/": {
                "request.dispatch": cherrypy.dispatch.MethodDispatcher()
            },
        }

        # An app can optionally have a dedicated directory for static assets
        static_path = os.path.join(app_dir, app, "static")
        if os.path.isdir(static_path):
            app_config["/static"] = {
                "tools.staticdir.on": True,
                "tools.staticdir.dir": os.path.realpath(static_path)
            }

        cherrypy.tree.mount(app_module.Controller(), url_path, app_config)

    # Customize the error page
    if cherrypy.config.get("request.show_tracebacks") is not False:
        cherrypy.config.update({
            "error_page.default": os.path.join(app_root, "error.html")
        })

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
    plugins.cache.Plugin(cherrypy.engine).subscribe()
    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    plugins.logger.Plugin(cherrypy.engine).subscribe()
    plugins.mpd.Plugin(cherrypy.engine).subscribe()
    plugins.notifier.Plugin(cherrypy.engine).subscribe()
    plugins.registry.Plugin(cherrypy.engine).subscribe()
    plugins.urlfetch.Plugin(cherrypy.engine).subscribe()

    # Tools
    cherrypy.tools.conditional_auth = tools.conditional_auth.Tool()
    cherrypy.tools.response_time = tools.response_time.Tool()
    cherrypy.tools.negotiable = tools.negotiable.Tool()
    cherrypy.tools.template = tools.template.Tool()
    cherrypy.tools.capture = tools.capture.Tool()

    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == '__main__':
    main()
