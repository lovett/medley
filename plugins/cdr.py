import cherrypy
from . import mixins

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """Query an Asterisk sqlite3 CDR database."""

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

        self.db_path = self._path("asterisk_cdr.sqlite")

        self._registerConverters()

    def start(self):
        self.bus.subscribe("cdr:call_count", self.callCount)
        self.bus.subscribe("cdr:call_log", self.callLog)
        self.bus.subscribe("cdr:call_history", self.callHistory)

    def stop(self):
        pass

    def callCount(self, src=None):
        if src:
            return self._selectOne(
                """SELECT count(*) as count FROM cdr WHERE src=?"""
                (src,)
            )

        return self._selectOne(
            """SELECT count(*) as count FROM cdr""",
            None
        )

    def callLog(self, src_exclude=[], dst_exclude=[], offset=0, limit=50):
        count = self.callCount()

        if count == 0:
            return ([], 0)

        query = """
        SELECT calldate as "date [naive_date]", end as "end_date [naive_date]",
        CASE LENGTH(src) WHEN 3 THEN "outgoing" else "incoming" END as direction,
        duration as "duration [duration]", clid as "clid [clid]",
        channel as "abbreviated_channel [channel]",
        dstchannel as "abbreviated_dstchannel [channel]", *
        FROM cdr
        WHERE 1=1"""

        if src_exclude:
            query += " AND src NOT IN ({}) ".format(",".join("?" * len(src_exclude)))

        if dst_exclude:
            query += " AND dst NOT IN ({}) ".format(",".join("?" * len(dst_exclude)))

        query += """
        ORDER BY calldate DESC
        LIMIT ? OFFSET ?"""

        params = []
        if src_exclude:
            params += src_exclude

        if dst_exclude:
            params += dst_exclude

        params += [limit, offset]

        result = self._select(query, params)

        return (result, count)

    def callHistory(self, caller, limit=0, offset=0):
        count = self.callCount(caller)

        if count == 0:
            return ([], 0)

        params = []

        query = """
        SELECT calldate as "date [naive_date]",
        CASE LENGTH(src) WHEN 3 THEN "outgoing" else "incoming" END as direction,
        duration as "duration [duration]",
        clid as "clid [clid]",
        *
        FROM cdr
        WHERE src=? OR dst LIKE ?
        ORDER BY calldate DESC
        """

        params.append(caller)
        params.append("%" + caller)

        if limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        if limit > 0 and offset > 0:
            query += " OFFSET ?"
            params.append(offset)

        result = self._select(query, params)

        return (result, count)
