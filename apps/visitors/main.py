import re
import cherrypy
import util.fs
import apps.logindex.models
from datetime import datetime, timedelta

class Controller:
    """Search website access logs"""

    name = "Visitors"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, q=None):
        log_root = cherrypy.engine.publish("registry:first_value", "logindex:root").pop()

        if not log_root:
            raise cherrypy.HTTPError(500, "No log root found in registry")

        site_domains = cherrypy.engine.publish(
            "registry:search",
            "logindex:site_domains",
            as_value_list=True
        ).pop()

        results = None
        active_query = None

        filters = {
            "ip": [],
            "include": [],
            "exclude": [],
            "shun": [],
            "date":  []
        }

        saved_queries = cherrypy.engine.publish("registry:search", "visitors*").pop()

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

        if len(filters["date"]) > 0:
            active_date = filters["date"][0]
        else:
            active_date = datetime.now().strftime("date %Y-%m-%d")


        if len(filters["ip"]) > 0:
            logman = apps.logindex.models.LogManager(log_root)
            offsets = logman.getLogOffsets("ip", filters["ip"])
            filters["date"] = offsets.keys()
            active_date = datetime.now().strftime("date %Y-%m-%d")
            del filters["ip"]

        results, duration = util.fs.appengine_log_grep(log_root, filters, offsets, 100)

        for index, result in enumerate(results.matches):
            result["ip_facts"] = cherrypy.engine.publish("ip:facts", result["ip"]).pop()

            if result.get("country"):
                result["ip_facts"]["geo"]["country_code"] = result.get("country")
                result["ip_facts"]["geo"]["region_code"] = result.get("region")
                result["ip_facts"]["geo"]["city"] = result.get("city")
                result["ip_facts"]["geo"]["country_name"] = cherrypy.engine.publish(
                    "geography:country_by_abbreviation",
                    result["country"]
                ).pop()


            if "," in result.get("latlong", ""):
                (lat, lng) = result["latlong"].split(",")
                result["ip_facts"]["geo"]["latitude"] = lat
                result["ip_facts"]["geo"]["longitude"] = lng

            try:
                result["delta"] = result["timestamp"] - results.matches[index + 1]["timestamp"]
            except (KeyError, IndexError):
                result["delta"] = None

        return {
            "html": ("visitors.html", {
                "q": q,
                "active_query": active_query,
                "active_date": active_date,
                "results": results.matches,
                "total_matches": results.count,
                "result_limit": results.limit,
                "duration": duration,
                "site_domains": site_domains,
                "saved_queries": saved_queries,
                "app_name": self.name
            })
        }
