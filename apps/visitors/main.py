"""Search website access logs"""

import re
from collections import namedtuple, defaultdict
import cherrypy
import pendulum

SavedQuery = namedtuple('SavedQuery', ['id', 'key', 'value', 'active'])


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    name = "Visitors"

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **kwargs):
        """Display a search interface, and the results of the default query"""

        query = kwargs.get('query')

        if query:
            query = query.strip()

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

        log_records, query_plan = cherrypy.engine.publish(
            "logindex:query",
            query
        ).pop() or []

        reversed_ips = None
        deltas = None
        durations = {}
        country_names = None
        annotations = None
        cookies = {}

        if log_records:
            reversed_ips = cherrypy.engine.publish(
                "logindex:query:reverse_ip",
                {record["ip"] for record in log_records}
            ).pop() or {}

            deltas = self.get_deltas(log_records)
            durations = self.get_durations(log_records)

            country_names = cherrypy.engine.publish(
                "geography:country_by_abbreviation",
                (record["country"] for record in log_records)
            ).pop()

            annotations = self.get_annotations(log_records)

            cookies = {
                record["ip"]: record["cookie"]
                for record in log_records
                if record["cookie"]
                and record["ip"] not in cookies
            }

        return {
            "html": ("visitors.jinja.html", {
                "flagless_countries": ("AP", None),
                "query": query,
                "query_plan": query_plan,
                "reversed_ips": reversed_ips,
                "active_date": self.get_active_date(log_records, query),
                "results": log_records,
                "country_names": country_names,
                "deltas": deltas,
                "durations": durations,
                "site_domains": site_domains,
                "saved_queries": saved_queries,
                "annotations": annotations,
                "cookies": cookies
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
    def get_durations(log_records):
        """Calculate visit duration per day per IP"""

        timezone = cherrypy.engine.publish(
            "registry:local_timezone"
        ).pop()

        maximums = defaultdict(int)
        minimums = defaultdict(int)

        for row in log_records:
            timestamp = row["unix_timestamp"]
            formatted_timestamp = pendulum.from_timestamp(
                timestamp
            ).in_timezone(timezone).format('YYYY-MM-DD')

            lookup_key = (row["ip"], formatted_timestamp)

            if lookup_key not in maximums or timestamp > maximums[lookup_key]:
                maximums[lookup_key] = timestamp
                continue

            if lookup_key not in minimums or timestamp < minimums[lookup_key]:
                minimums[lookup_key] = timestamp

        durations = {
            lookup_key: pendulum.duration(
                seconds=(maximums[lookup_key] - minimums[lookup_key])
            )
            for lookup_key in maximums
            if minimums[lookup_key] > 0
        }

        return durations

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
        """Figure out which date the query pertains to.

        This value is used by the calender widget in the UI.

        """

        if log_records:
            return log_records[0]["unix_timestamp"]

        timezone = cherrypy.engine.publish(
            "registry:local_timezone"
        ).pop()

        date_string = None

        matches = re.match(
            r"date\s+(\d{4}-\d{2})",
            query
        )

        if matches:
            date_string = matches.group(1) + "-01"

        matches = re.match(
            r"date\s+(\d{4}-\d{2}-\d{2})",
            query
        )

        if matches:
            date_string = matches.group(1)

        if date_string:
            active_date = pendulum.parse(
                date_string,
                tz=timezone
            )
        elif re.match(r"date\s+yesterday", query):
            active_date = pendulum.yesterday(tz=timezone)
        else:
            active_date = pendulum.today(tz=timezone)

        return active_date.start_of('day')

    @staticmethod
    def get_annotations(log_records):
        """Get IP address custom labels from the registry"""

        ips = {record["ip"] for record in log_records}

        keys = tuple(f"ip:{ip}" for ip in ips)

        return cherrypy.engine.publish(
            "registry:search",
            keys=keys,
            as_multivalue_dict=True,
            key_slice=1
        ).pop()
