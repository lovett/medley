import cherrypy
import pendulum
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
            "logindex:site_domain",
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

        log_records = cherrypy.engine.publish("logindex:query", q).pop() or []

        deltas = []
        for index, row in enumerate(log_records):
            if index == 0:
                active_date = row["unix_timestamp"]
            try:
                delta = pendulum.from_timestamp(row["unix_timestamp"]).diff_for_humans(
                    pendulum.from_timestamp(log_records[index + 1]["unix_timestamp"]),
                    True
                )
            except (KeyError, IndexError):
                delta = 0
            deltas.append(delta)


        countries = {record["country"] for record in log_records}

        country_names = {
            country: cherrypy.engine.publish("geography:country_by_abbreviation", country).pop()
            for country in countries
        }

        ips = {record["ip"] for record in log_records}
        annotation_keys = tuple("ip:{}".format(ip) for ip in ips)

        annotations = cherrypy.engine.publish(
            "registry:search",
            keys=annotation_keys,
            as_multivalue_dict=True,
            key_slice=1
        ).pop()

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
                "annotations": annotations,
                "app_url": cherrypy.engine.publish("url:for_controller", self).pop()
            })
        }
