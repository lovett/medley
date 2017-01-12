import cherrypy
import os.path
import os
import plugins.jinja
import plugins.audio
import inspect

import apps.headers.main
import apps.lettercase.main
import apps.ip.main
import apps.jenkins.main
import apps.topics.main
import apps.whois.main
import apps.geodb.main
import apps.registry.main
import apps.blacklist.main
import apps.awsranges.main
import apps.azure.main
import apps.later.main
import apps.archive.main
import apps.phone.main
import apps.logindex.main
import apps.visitors.main
import apps.captures.main
import apps.callerid.main
import apps.calls.main
import apps.countries.main
import apps.speak.main

import tools.negotiable
import tools.response_time
import tools.jinja
import tools.conditional_auth

class MedleyServer(object):

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="index.html")
    def index(self):
        """The application homepage lists the available endpoints"""

        user_facing_apps = []
        service_apps = []


        for name, controller in cherrypy.tree.apps.items():
            if not name:
                continue
            app_summary = controller.root.__doc__.strip().split("\n").pop(0)
            app = (name[1:], app_summary)
            if getattr(controller.root, "user_facing", False):
                user_facing_apps.append(app)
            else:
                service_apps.append(app)

        user_facing_apps.sort(key=lambda tup: tup[0])
        service_apps.sort(key=lambda tup:tup[0])

        return {
            "page_title": "Medley",
            "user_facing_apps": user_facing_apps,
            "service_apps": service_apps
        }

if __name__ == "__main__":
    app_root = os.path.dirname(os.path.abspath(__file__))

    cherrypy.config.update({
        "app_root": app_root,
        "tools.encode.on": False # Needed to get jinja templates working
    })

    # Load configuration from /etc/medley.conf if it exists, otherwise load
    # from the application root
    config_file = "/etc/medley.conf"
    if not os.path.isfile(config_file):
        config_file = os.path.join(app_root, "medley.conf")

    if not os.path.isfile(config_file):
        raise SystemExit("Exiting because a configuration file could not be found")

    cherrypy.config.update(config_file)

    # Create required application directories
    for key in ("database_dir", "cache_dir", "log_dir"):
        value = cherrypy.config.get(key)
        try:
            os.mkdir(value)
        except PermissionError:
            raise SystemExit("Unable to create {} directory".format(d))
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
    app_config = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher()
        },
        "/static": {
            "tools.staticdir.on": True,
            "tools.staticdir.dir": os.path.realpath("static")
        }
    }

    for name, cls in inspect.getmembers(apps, inspect.ismodule):
        try:
            path = "/{}".format(name)
            cherrypy.tree.mount(cls.main.Controller(), path, app_config)
        except AttributeError:
            pass

    # Attempt to drop privileges if daemonized
    if cherrypy.config.get("server.daemonize"):
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

        pid_file = cherrypy.config.get("server.pid")
        if pid_file:
            cherrypy.process.plugins.PIDFile(cherrypy.engine, pid_file).subscribe()

    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    plugins.audio.Plugin(cherrypy.engine).subscribe()

    cherrypy.engine.start()
    cherrypy.engine.block()
