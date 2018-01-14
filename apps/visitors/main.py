import cherrypy
from datetime import datetime, timedelta

class Controller:
    """Search website access logs"""

    name = "Visitors"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, q=None):
        site_domains = cherrypy.engine.publish(
            "registry:search",
            "logindex:site_domains",
            as_value_list=True
        ).pop()

        results = None
        active_query = None
        active_date = datetime.now()

        query_records = cherrypy.engine.publish(
            "registry:search",
            "visitors*"
        ).pop()

        saved_queries = []
        for record in query_records:
            id = record["rowid"]
            key = record["key"].replace("visitors:", "")
            value = record["value"]
            active = False

            if q:
                active = record["value"].split() == q.split()

            if key == "default" and not q:
                q = value
                active = True

            saved_queries.append((id, key, value, active))

        if not q:
            q = "date today"

        log_records = cherrypy.engine.publish("logindex:query", q).pop()

        deltas = []
        for index, row in enumerate(log_records):
            if index == 0:
                active_date = row["timestamp"]
            try:
                delta = row["timestamp"] - log_records[index + 1]["timestamp"]
            except (KeyError, IndexError):
                delta = 0
            deltas.append(delta)


        countries = {record["country"] for record in log_records}

        country_names = {
            country: cherrypy.engine.publish("geography:country_by_abbreviation", country).pop()
            for country in countries
        }

        return {
            "html": ("visitors.html", {
                "q": q,
                "active_date": active_date,
                "results": log_records,
                "country_names": country_names,
                "deltas": deltas,
                "site_domains": site_domains,
                "saved_queries": saved_queries,
                "app_name": self.name,
                "app_url": cherrypy.engine.publish("url:for_controller", self).pop()
            })
        }
