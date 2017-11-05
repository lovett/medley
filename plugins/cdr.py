import cherrypy
from . import mixins
from string import Template

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

    def callCount(self, src=None, src_exclude=[], dst_exclude=[]):
        query = Template("""
        SELECT count(*) as count FROM cdr
        WHERE 1=1 $srcTarget $srcFilter $dstFilter""")

        srcTarget = ""
        srcFilter = ""
        dstFilter = ""
        values = []

        if src:
            srcTarget = "AND src=?"
            values.push(src)

        if src_exclude:
            srcFilter = "AND src NOT IN ({})".format(",".join("?" * len(src_exclude)))
            values.extend(src_exclude)

        if dst_exclude:
            dstFilter = "AND dst NOT IN ({})".format(",".join("?" * len(dst_exclude)))
            values.extend(dst_exclude)

        query_str = query.substitute(
            srcTarget=srcTarget,
            srcFilter=srcFilter,
            dstFilter=dstFilter
        )

        row = self._selectOne(query_str, values)
        return row["count"]

    def callLog(self, src_exclude=[], dst_exclude=[], offset=0, limit=50):
        query = Template("""
        SELECT calldate as "date [naive_date]", end as "end_date [naive_date]",
        CASE LENGTH(src) WHEN 3 THEN "outgoing" else "incoming" END as direction,
        duration as "duration [duration]", clid as "clid [clid]",
        dstchannel as "abbreviated_dstchannel [channel]", src, dst
        FROM cdr
        WHERE 1=1 $srcFilter $dstFilter
        ORDER BY calldate DESC
        LIMIT ? OFFSET ?""")

        reversed_values = [offset, limit]
        dstExclude = ""
        srcExclude = ""

        if dst_exclude:
            dstFilter = "AND dst NOT IN ({})".format(",".join("?" * len(dst_exclude)))
            reversed_values.extend(dst_exclude)

        if src_exclude:
            srcFilter = "AND src NOT IN ({})".format(",".join("?" * len(src_exclude)))
            reversed_values.extend(src_exclude)

        query_str = query.substitute(srcFilter=srcFilter, dstFilter=dstFilter)

        return self._select(query_str, list(reversed(reversed_values)))

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
