import re
import cherrypy
import tools.negotiable
import tools.jinja
import requests
import util.ip
import urllib.parse
import apps.registry.models
import apps.logindex.models
import pycountry
import pytz
from datetime import datetime, timedelta

class Controller:
    """Search website access logs"""

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="visitors.html")
    @cherrypy.tools.negotiable()
    def GET(self, q=None):

        logman = apps.logindex.models.LogManager()
        registry = apps.registry.models.Registry()

        results = None
        active_query = None

        filters = {
            "ip": [],
            "include": [],
            "exclude": [],
            "shun": [],
            "date":  []
        }

        saved_queries = registry.search(key="visitors*")

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
            result["ip_facts"] = util.ip.facts(result["ip"], needs_geo_lookup)

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
