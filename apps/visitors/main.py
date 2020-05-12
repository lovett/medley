"""Website traffic viewer"""

import re
import sqlite3
import typing
from collections import namedtuple
import cherrypy
import pendulum

SavedQuery = namedtuple('SavedQuery', ['id', 'key', 'value', 'active'])


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *_args: str, **kwargs: str) -> bytes:
        """Display a search interface, and the results of the default query"""

        query = kwargs.get("query", "")

        if query:
            query = query.strip()

        site_domains = cherrypy.engine.publish(
            "registry:search:valuelist",
            "logindex:site_domain",
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
        country_names = None
        annotations = None
        cookies: typing.Dict[str, str] = {}

        if log_records:
            reversed_ips = cherrypy.engine.publish(
                "logindex:query:reverse_ip",
                {record["ip"] for record in log_records}
            ).pop() or {}

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

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/visitors/visitors.jinja.html",
                flagless_countries=("AP", None),
                query=query,
                query_plan=query_plan,
                reversed_ips=reversed_ips,
                active_date=self.get_active_date(log_records, query),
                results=log_records,
                country_names=country_names,
                site_domains=site_domains,
                saved_queries=saved_queries,
                annotations=annotations,
                cookies=cookies
            ).pop()
        )

    @staticmethod
    def get_saved_queries(current_query: str = "") -> typing.List[SavedQuery]:
        """Fetch and restructure saved search queries"""

        _, rows = cherrypy.engine.publish(
            "registry:search",
            "visitors*"
        ).pop()

        queries = []

        for row in rows:
            record_id = row["rowid"]
            key = row["key"].replace("visitors:", "")
            value = row["value"]
            active = False

            if current_query:
                active = row["value"].split() == current_query.split()

            if key == "default" and not current_query:
                active = True

            queries.append(SavedQuery(record_id, key, value, active))

        return queries

    @staticmethod
    def get_active_date(
            log_records: typing.List[sqlite3.Row],
            query: str
    ) -> pendulum.DateTime:
        """Figure out which date the query pertains to."""

        if log_records:
            return pendulum.from_timestamp(
                log_records[0]["unix_timestamp"]
            )

        timezone = cherrypy.engine.publish(
            "registry:timezone"
        ).pop()

        query_date = ""

        if re.match(r"date\s+yesterday", query):
            query_date = "yesterday"

        if not query_date:
            # Look for YYYY-MM-DD.
            matches = re.match(
                r"date\s+(\d{4}-\d{2}-\d{2})",
                query
            )

            if matches:
                query_date = matches.group(1)

        if not query_date:
            # Look for YYYY-MM
            matches = re.match(
                r"date\s+(\d{4}-\d{2})",
                query
            )

            if matches:
                query_date = matches.group(1) + "-01"

        if query_date == "":
            active_date = pendulum.today()
        elif query_date == "yesterday":
            active_date = pendulum.yesterday()
        else:
            active_date = typing.cast(
                pendulum.DateTime,
                pendulum.parse(query_date)
            )

        return typing.cast(
            pendulum.DateTime,
            active_date.in_tz(timezone).start_of('day')
        )

    @staticmethod
    def get_annotations(
            log_records: typing.List[sqlite3.Row]
    ) -> typing.Dict[str, str]:
        """Get IP address custom labels from the registry"""

        ips = {record["ip"] for record in log_records}

        keys = tuple(f"ip:{ip}" for ip in ips)

        return typing.cast(
            typing.Dict[str, str],
            cherrypy.engine.publish(
                "registry:search:multidict",
                keys=keys,
                key_slice=1
            ).pop()
        )
