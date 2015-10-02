import cherrypy
import time
import os.path
import os
import pwd
import subprocess
import re
import urllib.parse
import IPy
import json
import plugins.jinja
import pycountry
import inspect
import util.phone
import util.asterisk
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
import apps.loginventory.main
import apps.azure.main
import apps.later.main

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
    @cherrypy.tools.template(template="phone.html")
    def phone(self, number=None, cid_number=None, cid_value=None):
        """Get the geographic location and recent call history for a phone number"""

        data = {}
        config = cherrypy.request.app.config["asterisk"]

        if cid_number and cid_value:
            sock = util.asterisk.authenticate(config)

            if not sock:
                raise cherrypy.HTTPError(500, "Unable to authenticate with Asterisk")

            result = util.asterisk.save_callerid(sock, cid_number, cid_value)

            if not result:
                raise cherrypy.HTTPError(500, "Failed to save caller id")

            sock.close()
            cherrypy.response.status = 204
            return

        if number is None:
            message = "Phone number not specified"
            if cherrypy.request.as_json:
                cherrypy.response.status = 400
                return {
                    "message": message
                }
            elif cherrypy.request.as_text:
                raise cherrypy.HTTPError(400, message)
            else:
                return data

        number = util.phone.sanitize(number)
        area_code = number[:3]

        if len(area_code) is not 3:
            if cherrypy.request.as_json:
                cherrypy.response.status = 400
                return {
                    "message": "Invalid number"
                }
            else:
                raise cherrypy.HTTPError(400, "Invalid number")

        def phone_query():
            try:
                return util.phone.findAreaCode(area_code)
            except (AssertionError, util.phone.PhoneException):
                return {}

        key = "phone:{}".format(area_code)
        location = self.cache.get_or_create(
            key, phone_query,
            should_cache_fn= lambda v: v is not None
        )

        sock = util.asterisk.authenticate(config)

        if sock:
            caller_id = util.asterisk.get_callerid(sock, number)
            blacklisted = util.asterisk.get_blacklist(sock, number)
            sock.close()
        else:
            caller_id = None
            blacklisted = None

        history = util.phone.callHistory(cherrypy.config.get("asterisk.cdr_db"), number, 5)

        if not caller_id:
            try:
                caller_id = history[0][0]["clid"]
            except IndexError:
                caller_id = "Unknown"

        if cherrypy.request.as_text:
            return location.get("state_name", "Unknown")
        else:
            data["caller_id"] = caller_id
            data["history"] = history[0]
            data["number"] = number
            data["blacklisted"] = blacklisted
            data["number_formatted"] = util.phone.format(number)
            data["state_abbreviation"] = location.get("state_abbreviation")
            data["state_name"] = location.get("state_name")
            data["whitepages_url"] = "http://www.whitepages.com/phone/" + number
            data["bing_url"] = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(data["number_formatted"])
            data["comment"] = location.get("comment")
            data["sparql"] = location.get("sparql", [])

            return data

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="archive.html")
    def archive(self, date=None, q=None, action=None, bookmark_id=None):
        """View and search saved bookmarks"""

        if action == "delete" and bookmark_id:
            util.db.deleteBookmark(bookmark_id)
            return "OK".encode("UTF-8")
            cherrypy.response.status = 204
            return

        entries = OrderedDict()
        timezone = pytz.timezone(cherrypy.config.get("timezone"))

        if not q:
            bookmarks = util.db.getRecentBookmarks(limit=50)
        else:
            bookmarks = util.db.searchBookmarks(q)

        for bookmark in bookmarks:
            key = bookmark["created"].astimezone(timezone)
            key = key.strftime("%Y-%m-%d")

            if not key in entries:
                entries[key] = []

            entries[key].append(bookmark)

        return {
            "entries": entries
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

    @util.decorator.hideFromHomepage
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.encode()
    @util.decorator.timed
    def logindex(self, date=None, filename=None, by=None, match=None):
        start_time = time.time()

        if filename:
            date = filename.replace(".log", "")

        try:
            date = datetime.strptime(date, "%Y-%m-%d")
        except:
            raise cherrypy.HTTPError(400, "Date could not be parsed as %Y-%m-%d")

        if by is None:
            raise cherrypy.HTTPError(400, "Field name to index by not specified")

        log_file = "{}/{}/{}".format(
            cherrypy.request.app.config["/visitors"].get("log_dir"),
            date.strftime("%Y-%m"),
            date.strftime("%Y-%m-%d.log"))

        if not os.path.isfile(log_file):
            raise cherrypy.HTTPError(400, "No log for that date")

        index_name = by
        if match:
            lower_match = match.lower()
            index_name += "_" + lower_match

        db_conn = util.db.openLogIndex(
            cherrypy.config.get("database_dir"),
            index_name
        )

        value_batch = []
        line_count = 0

        def addBatch(batch):
            if len(batch) == 0:
                return

            util.db.indexLogLines(
                db_conn,
                index_name,
                batch
            )


        if by == "ip":
            indexer = util.parse.appengine_ip
        else:
            indexer = util.parse.appengine

        with open(log_file, "r") as f:
            max_offset = util.db.getMaxOffset(
                db_conn, index_name, date
            )

            f.seek(max_offset)

            while True:
                offset = f.tell()
                line = f.readline()
                if not line:
                    break

                fields = indexer(line)

                # the field isn't present
                if not by in fields:
                    continue

                # the field doesn't match
                if match and (lower_match not in fields[by].lower()):
                    continue

                values = (
                    date.strftime("%Y-%m-%d"),
                    fields[by],
                    offset
                )

                value_batch.append(values)

                if len(value_batch) > 500:
                    addBatch(value_batch)
                    line_count += len(value_batch)
                    value_batch = []

        addBatch(value_batch)
        line_count += len(value_batch)
        value_batch = []

        util.db.closeLogIndex(db_conn)

        cherrypy.response.status = 204
        return line_count

    @util.decorator.hideFromHomepage
    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.encode()
    def logwalk(self, by, distance=7, match=None, all=None):
        log_files = self.loginventory()

        if all:
            start_index = 0
        else:
            start_index = int(distance) * -1

        log_subset = log_files[start_index:]

        results = []
        for log in log_subset:
            lines_processed, duration = self.logindex(filename=log, by=by, match=match)
            results.append("{}: {} lines in {}".format(log, lines_processed, duration))

        cherrypy.response.status = 200
        cherrypy.response.headers["Content-Type"] = "text/plain"
        return "\n".join(results) + "\n\n"

    @cherrypy.expose
    @cherrypy.tools.negotiable()
    @cherrypy.tools.template(template="visitors.html")
    def visitors(self, q=None):
        """Search website access logs"""

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
            db_conn = util.db.openLogIndex(
                cherrypy.config.get("database_dir"),
            )

            offsets = util.db.getLogOffsets(db_conn, "ip", filters["ip"])

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
