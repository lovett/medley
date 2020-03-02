"""Query an Asterisk sqlite3 CDR database."""

import sqlite3
import typing
import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for querying an Asterisk CDR database."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("asterisk_cdr.sqlite")

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the cdr prefix.
        """
        self.bus.subscribe("cdr:timeline", self.timeline)
        self.bus.subscribe("cdr:history", self.history)

    def timeline(
            self,
            src_exclude: typing.Tuple[str, ...] = (),
            dst_exclude: typing.Tuple[str, ...] = (),
            offset: int = 0,
            limit: int = 50
    ) -> typing.Tuple[typing.List[sqlite3.Row], int]:
        """Get a list of calls in reverse-chronological order."""

        reversed_values = [str(offset), str(limit)]
        dst_filter = ""
        src_filter = ""

        if dst_exclude:
            exclusions = ",".join("?" * len(dst_exclude))
            dst_filter = f"AND dst NOT IN ({exclusions})"
            reversed_values.extend(dst_exclude)

        if src_exclude:
            exclusions = ",".join("?" * len(src_exclude))
            src_filter = f"AND src NOT IN ({exclusions})"
            reversed_values.extend(src_exclude)

        sql = f"""
        SELECT calldate as "date [calldate_to_utc]", end as
        "end_date [calldate_to_utc]",
        CASE LENGTH(src)
          WHEN 3 THEN "outgoing"
          ELSE "incoming"
          END AS direction,
        duration AS "duration [duration]",
        clid AS "clid [clid]",
        src, dst
        FROM cdr
        WHERE 1=1 {src_filter} {dst_filter}
        ORDER BY calldate DESC
        LIMIT ? OFFSET ?"""

        return (
            self._select(sql, tuple(reversed(reversed_values))),
            self._count(sql, tuple(reversed(reversed_values))),
        )

    def history(
            self,
            number: str,
            limit: int = 50
    ) -> typing.Tuple[typing.List[sqlite3.Row], int]:
        """An abbreviated version of log() for a single number.

        Puts more emphasis on whether a call was placed or received.

        """

        sql = """
        SELECT calldate as "date [calldate_to_utc]",
        CASE LENGTH(src)
          WHEN 3 THEN "outgoing"
          ELSE "incoming"
          END AS direction,
        duration as "duration [duration]", clid as "clid [clid]"
        FROM cdr
        WHERE src LIKE ? OR dst LIKE ?
        ORDER BY calldate DESC
        LIMIT ?
        """

        wildcard_number = f"%{number}"

        return (
            self._select(sql, (wildcard_number, wildcard_number, limit)),
            self._count(sql, (wildcard_number, wildcard_number, limit))
        )
