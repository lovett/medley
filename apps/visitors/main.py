import re
import cherrypy
import tools.negotiable
import tools.jinja
import requests
import util.ip
import urllib.parse
import apps.registry.models
import apps.logindex.models
import pytz
from datetime import datetime, timedelta

class Controller:
    """Search website access logs"""

    name = "Visitors"

    exposed = True

    user_facing = True

    @cherrypy.tools.template(template="visitors.html")
    @cherrypy.tools.negotiable()
    def GET(self, q=None):
        registry = apps.registry.models.Registry()
        roots = registry.search(key="logindex:root")
        if not roots:
            raise cherrypy.HTTPError(500, "No log roots found in registry")

        site_domains = [row.value for row in registry.search(key="logindex:site_domains")]
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
        q = re.sub(",\s*", "\n", q)
        q = q.strip()

        for line in q.split("\n"):
            try:
                subject, value = line.strip().split(" ", 1)
                filters[subject].append(value)
            except (ValueError, KeyError):
                continue

        offsets = None

        if len(filters["ip"]) > 0:
            logman = apps.logindex.models.LogManager(roots[0]["value"])
            offsets = logman.getLogOffsets("ip", filters["ip"])
            filters["date"] = offsets.keys()
            del filters["ip"]

        results, duration = util.fs.appengine_log_grep(roots[0]["value"], filters, offsets, 100)

        for index, result in enumerate(results.matches):
            result["ip_facts"] = util.ip.facts(result["ip"])
            if result.get("country"):
                result["ip_facts"]["geo"]["country_code"] = result.get("country")
                result["ip_facts"]["geo"]["region_code"] = result.get("region")
                result["ip_facts"]["geo"]["city"] = result.get("city")
                registry_key = "country_code:alpha2:{}".format(result["country"])
                result["ip_facts"]["geo"]["country_name"] = registry.first(registry_key, limit=1)


            if "," in result.get("latlong", ""):
                (lat, lng) = result["latlong"].split(",")
                result["ip_facts"]["geo"]["latitude"] = lat
                result["ip_facts"]["geo"]["longitude"] = lng

            try:
                result["delta"] = result["timestamp"] - results.matches[index + 1]["timestamp"]
            except (KeyError, IndexError):
                result["delta"] = None

        return {
            "q": q,
            "active_query": active_query,
            "results": results.matches,
            "total_matches": results.count,
            "result_limit": results.limit,
            "duration": duration,
            "site_domains": site_domains,
            "saved_queries": saved_queries,
            "app_name": self.name
        }
