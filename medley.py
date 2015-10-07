import cherrypy
import time
import os.path
import os
import pwd
import subprocess
import re
import IPy
import json
import plugins.jinja
import pycountry
import inspect
import util.phone
import util.net
import util.html
import util.fs
import util.db
import util.decorator
import dogpile.cache
import pytz
import time
import html.parser
import syslog
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

import apps.headers.main
import apps.lettercase.main
import apps.ip.main
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
import apps.logindex.models

import tools.negotiable
import tools.response_time
import tools.jinja
import tools.conditional_auth
import tools.capture

class MedleyServer(object):
    mc = None
    geoip = None
    cache = dogpile.cache.make_region()

    def __init__(self):
        syslog.openlog(self.__class__.__name__)

        db_dir = os.path.realpath(cherrypy.config.get("database_dir"))

        util.db.setup(db_dir)
        util.db.geoSetup(db_dir, cherrypy.config.get("geoip.download.url"))

        self.cache.configure_from_config(cherrypy.config, "cache.")

    @util.decorator.hideFromHomepage
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="index.html")
    def index(self):
        """The application homepage lists the available endpoints"""

        endpoints = []

        # The old way: apps are defined in the server class and
        # configured for display on the homepage via decorator. This
        # should go away once all apps have been refactored out of the
        # server class.
        for name, value in inspect.getmembers(self, inspect.ismethod):
            if name == "index":
                continue

            exposed = getattr(value, "exposed", False)
            hidden = getattr(value, "hide_from_homepage", False)

            if exposed and not hidden:
                endpoints.append((name, value.__doc__))

        # the new way: apps are discrete classes mounted onto the
        # server and configured for display on the homepage via a
        # class attribute
        for name, controller in cherrypy.tree.apps.items():
            if getattr(controller.root, "user_facing", False):
                endpoints.append((name[1:], controller.root.__doc__))

        endpoints.sort(key=lambda tup: tup[0])

        if cherrypy.request.as_text:
            output = ""
            for name, description in endpoints:
                output += "/" + name + "\n"
                output += str(description) + "\n\n"
            return output
        elif cherrypy.request.as_json:
            return endpoints
        else:
            return {
                "page_title": "Medley",
                "endpoints": endpoints
            }

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="captures.html")
    def captures(self, q=None):
        """Display captured requests"""

        return {
            "q": q,
            "captures": util.db.getCaptures(q)
        }

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="visitors.html")
    def visitors(self, q=None):
        """Search website access logs"""
        logman = apps.logindex.models.LogManager()

        results = None
        active_query = None

        filters = {
            "ip": [],
            "include": [],
            "exclude": [],
            "shun": [],
            "date":  []
        }

        saved_queries = util.db.getAnnotationsByPrefix("visitors")

        if q:
            for query in saved_queries:
                if re.sub("\s", "", q, flags=re.UNICODE) == re.sub("\s", "", query["value"], flags=re.UNICODE):
                    active_query = query["key"]
                    break

        if not q:
            try:
                active_query, q = [(query["key"], query["value"]) for query in saved_queries
                     if query["key"] == "visitors:default"][0]
            except IndexError:
                q = ""


        q = re.sub("[^\d\w -:;,\n]+", "", q, flags=re.UNICODE)
        q = q.replace("date today", datetime.now().strftime("date %Y-%m-%d"))
        q = q.replace("date yesterday", (datetime.now() - timedelta(days=1)).strftime("date %Y-%m-%d"))

        if "," in q:
            q = q.replace(",", "\n")

        for line in q.split("\n"):
            try:
                subject, value = line.strip().split(" ", 1)
                filters[subject].append(value)
            except (ValueError, KeyError):
                continue

        log_dir = cherrypy.request.config.get("log_dir")

        offsets = None

        if len(filters["ip"]) > 0:
            offsets = logman.getLogOffsets("ip", filters["ip"])
            filters["date"] = offsets.keys()
            del filters["ip"]


        results, duration = util.fs.appengine_log_grep(log_dir, filters, offsets, 100)

        for index, result in enumerate(results.matches):
            needs_geo_lookup = "country" not in result
            result["ip_facts"] = util.db.ipFacts(result["ip"], needs_geo_lookup)

            if not needs_geo_lookup:
                result["ip_facts"]["geo"]["country_code"] = result["country"]
                result["ip_facts"]["geo"]["region_code"] = result["region"]
                result["ip_facts"]["geo"]["city"] = result["city"]
                if result["country"]:
                    result["ip_facts"]["geo"]["country_name"] = pycountry.countries.get(alpha2=result["country"]).name
                if "," in result.get("latlong"):
                    (lat, lng) = result["latlong"].split(",")
                    result["ip_facts"]["geo"]["latitude"] = lat
                    result["ip_facts"]["geo"]["longitude"] = lng

            try:
                result["delta"] = result["timestamp"] - results.matches[index + 1]["timestamp"]
            except IndexError:
                result["delta"] = None

        return {
            "q": q,
            "active_query": active_query,
            "results": results.matches,
            "total_matches": results.count,
            "result_limit": results.limit,
            "duration": duration,
            "site_domains": cherrypy.request.config.get("site_domains"),
            "saved_queries": saved_queries
        }


if __name__ == "__main__":
    app_root = os.path.dirname(os.path.abspath(__file__))

    # Application directory paths have default values that are
    # relative to the app root.
    cherrypy.config.update({
        "database_dir": os.path.realpath("db"),
        "log_dir": os.path.realpath("logs")
    })

    # Application configuration is sourced from multiple places:
    #
    #   /etc/medley.conf: The main config. It is kept outside the app
    #   root so that it remains untouched during deployment.
    #
    #   default.conf: The default config. Only used if the main
    #   config does not exist.
    #
    #   local.conf: The local config. Used to override values from the
    #   main or default config, mainly for the benefit of development
    #   so that you can change a few values without making a full copy
    #   of the default config.
    #
    # Since configuration files can contain both global and
    # application-specific sections, they are first applied to the
    # CherryPy global config and then again to the application config.

    default_config = "/etc/medley.conf"
    if not os.path.isfile(default_config):
        default_config = os.path.join(app_root, "default.conf")

    cherrypy.config.update(default_config)
    app = cherrypy.tree.mount(MedleyServer(), config=default_config)

    local_config = os.path.join(app_root, "local.conf")
    if os.path.isfile(local_config):
        cherrypy.config.update(local_config)
        app.merge(local_config)

    app_config = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher()
        }
    }

    for name, cls in inspect.getmembers(apps, inspect.ismodule):
        path = "/{}".format(name)
        cherrypy.tree.mount(cls.main.Controller(), path, app_config)

    # Logging occurs either to stdout or to files. For file logging,
    # the configuration should specify a value for log_dir and ignore
    # the log.access_file and log.error.file settings described in the
    # CherryPy documentation. This approach allows the application to
    # create the log directory if it doesn't exist.
    if not cherrypy.config.get("log.screen"):
        log_dir = cherrypy.config.get("log_dir")
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        cherrypy.config.update({
            "log.access_file": os.path.join(log_dir, "access.log"),
            "log.error_file": os.path.join(log_dir, "error.log")
        })

    # Attempt to drop privileges if daemonized
    if cherrypy.config.get("server.daemonize"):
        cherrypy.process.plugins.Daemonizer(cherrypy.engine).subscribe()

        pid_file = cherrypy.config.get("server.pid")
        if pid_file:
            cherrypy.process.plugins.PIDFile(cherrypy.engine, pid_file).subscribe()

    plugins.jinja.Plugin(cherrypy.engine).subscribe()

    cherrypy.engine.start()
    cherrypy.engine.block()
