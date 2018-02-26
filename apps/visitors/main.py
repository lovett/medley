"""Search website access logs"""

import re
from collections import namedtuple
import cherrypy
import pendulum

SavedQuery = namedtuple('SavedQuery', ['id', 'key', 'value', 'active'])


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    name = "Visitors"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, query=None):
        """Display a search interface, and the results of the default query"""

        site_domains = cherrypy.engine.publish(
            "registry:search",
            "logindex:site_domain",
            as_value_list=True
        ).pop()

        saved_queries = self.get_saved_queries(query)

        if not query:
            query = next(
                (query.value for query in saved_queries if query.active),
                "date today"
            )

        log_records = cherrypy.engine.publish(
            "logindex:query",
            query
        ).pop() or []

        deltas = self.get_deltas(log_records)

        active_date = self.get_active_date(log_records, query)

        countries = {record["country"] for record in log_records}

        country_names = {
            country: cherrypy.engine.publish(
                "geography:country_by_abbreviation", country
            ).pop()
            for country in countries
        }

        annotations = self.get_annotations(log_records)

        app_url = cherrypy.engine.publish(
            "url:for_controller",
            self
        ).pop()

        return {
            "html": ("visitors.html", {
                "query": query,
                "active_date": active_date,
                "results": log_records,
                "country_names": country_names,
                "deltas": deltas,
                "site_domains": site_domains,
                "saved_queries": saved_queries,
                "app_name": self.name,
                "annotations": annotations,
                "app_url": app_url
            })
        }

    @staticmethod
    def get_saved_queries(current_query=None):
        """Fetch and restructure saved search queries"""

        records = cherrypy.engine.publish(
            "registry:search",
            "visitors*"
        ).pop()

        queries = []

        for record in records:
            record_id = record["rowid"]
            key = record["key"].replace("visitors:", "")
            value = record["value"]
            active = False

            if current_query:
                active = record["value"].split() == current_query.split()

            if key == "default" and not current_query:
                active = True

            queries.append(SavedQuery(record_id, key, value, active))

        return queries

    @staticmethod
    def get_deltas(log_records):
        """Calculate elapsed time intervals between records"""

        deltas = []
        for index, row in enumerate(log_records):
            try:
                current_timestamp = pendulum.from_timestamp(
                    row["unix_timestamp"]
                )

                previous_timestamp = pendulum.from_timestamp(
                    log_records[index + 1]["unix_timestamp"]
                )

                delta = current_timestamp.diff_for_humans(
                    previous_timestamp,
                    True
                )
            except (KeyError, IndexError):
                delta = 0

            deltas.append(delta)

        return deltas

    @staticmethod
    def get_active_date(log_records, query):
        """
        Figure out which date the query pertains to

        This value is used by the calender widget in the UI
        """

        if log_records:
            return log_records[1]

        timezone = cherrypy.engine.publish(
            "registry:first_value",
            "config:timezone",
            memorize=True
        ).pop()

        try:
            date_string = re.match(
                r"date\s+(\d{4}-\d{2}-\d{2})",
                query
            ).group(1)

            active_date = pendulum.from_format(
                date_string,
                '%Y-%m-%d',
                timezone
            )

        except AttributeError:
            active_date = pendulum.now()

        return active_date

    @staticmethod
    def get_annotations(log_records):
        """Get IP address custom labels from the registry"""

        ips = {record["ip"] for record in log_records}

        keys = tuple("ip:{}".format(ip) for ip in ips)

        return cherrypy.engine.publish(
            "registry:search",
            keys=keys,
            as_multivalue_dict=True,
            key_slice=1
        ).pop()
