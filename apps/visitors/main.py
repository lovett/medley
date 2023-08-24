"""Website traffic viewer"""

from datetime import date, datetime
import re
import sqlite3
from typing import Dict
from typing import List
from typing import Union
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, **kwargs: str) -> bytes:
        """Display a search interface, and the results of the default query"""

        query = kwargs.get("query", "")

        site_domains = cherrypy.engine.publish(
            "registry:search:valuelist",
            "logindex:site_domain",
        ).pop()

        saved_queries = cherrypy.engine.publish(
            "registry:search:dict",
            "visitors*",
            key_slice=1
        ).pop()

        registry_url = cherrypy.engine.publish(
            "app_url",
            "/registry"
        ).pop()

        if "default" in saved_queries.keys() and not query:
            query = saved_queries["default"]

        log_records, query_plan = cherrypy.engine.publish(
            "logindex:query",
            query
        ).pop() or []

        reversed_ips = None
        country_names = None
        annotations = None
        cookies: Dict[str, str] = {}

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

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/visitors/visitors.jinja.html",
            flagless_countries=("AP", None, ""),
            query=query,
            query_plan=query_plan,
            reversed_ips=reversed_ips,
            active_date=self.get_active_date(log_records, query),
            results=log_records,
            country_names=country_names,
            registry_url=registry_url,
            site_domains=site_domains,
            saved_queries=saved_queries,
            annotations=annotations,
            cookies=cookies
        ).pop()

    @staticmethod
    def get_active_date(
            log_records: List[sqlite3.Row],
            query: str,
    ) -> Union[date, datetime]:
        """Figure out which date the query pertains to."""

        query_date = ""

        if log_records:
            return cherrypy.engine.publish(
                "clock:from_timestamp",
                log_records[0]["unix_timestamp"]
            ).pop()

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

        if query_date in ("today", "yesterday"):
            now = cherrypy.engine.publish(
                "clock:now",
                local=True
            ).pop()

            if query_date == "yesterday":
                active_date = cherrypy.engine.publish(
                    "clock:shift",
                    now,
                    days=-1
                ).pop()
        else:
            active_date = cherrypy.engine.publish(
                "clock:from_format",
                query_date,
                "%Y-%m-%d"
            ).pop()

        return active_date

    @staticmethod
    def get_annotations(
            log_records: List[sqlite3.Row]
    ) -> Dict[str, str]:
        """Get IP address custom labels from the registry"""

        ips = {record["ip"] for record in log_records}

        keys = tuple(f"ip:{ip}" for ip in ips)

        return cherrypy.engine.publish(
            "registry:search:multidict",
            keys=keys,
            key_slice=1
        ).pop()
