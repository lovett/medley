"""Query an Asterisk sqlite3 CDR database."""

from string import Template
import cherrypy
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for querying an Asterisk CDR database."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("asterisk_cdr.sqlite")

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the cdr prefix.
        """
        self.bus.subscribe("cdr:call_count", self.call_count)
        self.bus.subscribe("cdr:call_log", self.call_log)
        self.bus.subscribe("cdr:call_history", self.call_history)

    def call_count(self, src=None, src_exclude=(), dst_exclude=()):
        """Get the number of calls made or received by a number."""

        query = Template("""
        SELECT count(*) as count FROM cdr
        WHERE 1=1 $src_target $src_filter $dst_filter""")

        src_target = ""
        src_filter = ""
        dst_filter = ""
        values = []

        if src:
            src_target = "AND src=?"
            values.append(src)

        if src_exclude:
            src_filter = "AND src NOT IN ({})".format(
                ",".join("?" * len(src_exclude))
            )
            values.extend(src_exclude)

        if dst_exclude:
            dst_filter = "AND dst NOT IN ({})".format(
                ",".join("?" * len(dst_exclude))
            )
            values.extend(dst_exclude)

        query_str = query.substitute(
            src_target=src_target,
            src_filter=src_filter,
            dst_filter=dst_filter
        )

        row = self._selectOne(query_str, values)
        return row["count"]

    def call_log(self, src_exclude=(), dst_exclude=(), offset=0, limit=50):
        """Get a list of calls in reverse-chronological order."""

        query = Template("""
        SELECT calldate as "date [calldate_to_utc]", end as "end_date [calldate_to_utc]",
        CASE LENGTH(src)
          WHEN 3 THEN "outgoing"
          ELSE "incoming"
          END AS direction,
        duration AS "duration [duration]",
        clid AS "clid [clid]",
        src, dst
        FROM cdr
        WHERE 1=1 $src_filter $dst_filter
        ORDER BY calldate DESC
        LIMIT ? OFFSET ?""")

        reversed_values = [offset, limit]
        dst_filter = ""
        src_filter = ""

        if dst_exclude:
            dst_filter = "AND dst NOT IN ({})".format(
                ",".join("?" * len(dst_exclude))
            )

            reversed_values.extend(dst_exclude)

        if src_exclude:
            src_filter = "AND src NOT IN ({})".format(
                ",".join("?" * len(src_exclude))
            )

            reversed_values.extend(src_exclude)

        query_str = query.substitute(
            src_filter=src_filter,
            dst_filter=dst_filter
        )

        return self._select(query_str, list(reversed(reversed_values)))

    def call_history(self, number, limit=50):
        """An abbreviated version of call_log() for a single number.

        Puts more emphasis on whether a call was placed or received.

        """

        query = """
        SELECT calldate as "date [calldate_to_utc]",
        CASE LENGTH(src)
          WHEN 3 THEN "outgoing"
          ELSE "incoming"
          END AS direction,
        duration as "duration [duration]", clid as "clid [clid]"
        FROM cdr
        WHERE src=? OR dst LIKE ?
        ORDER BY calldate DESC
        LIMIT ?
        """

        return self._select(
            query,
            (number, "%" + number, limit)
        )
