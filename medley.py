"""Medley, a collection of web-based utilities.

Medley is a hub for miniature applications that each do one thing
reasonably well and might otherwise be one-off or throwaway scripts.

Putting them under a common roof means not having to start from zero
each time, and makes it easier to leverage existing things when build
new things.
"""

import datetime
import email.utils
import importlib
import os
import os.path
import time
import cherrypy
import plugins
import tools


class MedleyServer(object):
    """The core application onto which individual apps are mounted."""

    name = "Medley"

    apps = []

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="index.html")
    def index(self):
        """The application homepage lists the available endpoints"""

        if not self.apps:
            for name, controller in cherrypy.tree.apps.items():
                if not name:
                    continue

                summary = controller.root.__doc__.strip().split("\n").pop(0)

                user_facing = getattr(controller.root, "user_facing", False)

                app = (name[1:], summary, user_facing)

                self.apps.append(app)

                self.apps.sort(key=lambda tup: tup[0])

        expiration = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        expiration = time.mktime(expiration.timetuple())
        cherrypy.response.headers["Expires"] = email.utils.formatdate(
            timeval=expiration,
            localtime=False,
            usegmt=True
        )

        return {
            "page_title": self.name,
            "apps": self.apps,
        }


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

    # Jinja templating won't work unlss tools.encode is off
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

    # Mount the core server
    cherrypy.tree.mount(MedleyServer(), config={
        "/static": {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": os.path.realpath("static")
        }
    })

    # Mount the apps
    app_dir = os.path.join(os.path.dirname(__file__), "apps")

    for item in os.listdir(app_dir):
        main_path = os.path.join(app_dir, item, "main.py")
        if not os.path.isfile(main_path):
            continue

        module = importlib.import_module("apps.{}.main".format(item))

        cherrypy.tree.mount(module.Controller(), "/{}".format(item), {
            "/": {
                "request.dispatch": cherrypy.dispatch.MethodDispatcher()
            },
            "/static": {
                "tools.staticdir.on": True,
                "tools.staticdir.dir": os.path.realpath("static")
            }
        })

    # Customize the error page
    if cherrypy.config.get("request.show_tracebacks") is not False:
        cherrypy.config.update({
            "error_page.default": os.path.join(app_root, "static/error.html")
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
    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    plugins.mpd.Plugin(cherrypy.engine).subscribe()

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
