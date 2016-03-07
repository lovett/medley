import sys
import syslog
import time
import datetime
import os.path
import tools.negotiable
import apps.logindex.models
import apps.registry.models
import util.decorator
import cherrypy

class Controller:
    """Index log files"""

    name = "Log Index"

    exposed = True

    user_facing = False

    syslog_ident = "medley:logindex"

    def parseLogDate(self, s):
        s = s.replace(".log", "")
        try:
            return datetime.datetime.strptime(s, "%Y-%m-%d")
        except:
            raise cherrypy.HTTPError(400, "Unable to parse a date from {}".format(s))

    @cherrypy.tools.encode()
    def POST(self, start, end=None, by="ip", match=None):
        start_time = time.time()
        one_day = datetime.timedelta(days=1)

        registry = apps.registry.models.Registry()
        roots = registry.search(key="logindex:root")
        if not roots:
            raise cherrypy.HTTPError(500, "No log roots found in registry")

        start_date = self.parseLogDate(start)
        logman = apps.logindex.models.LogManager(roots[0]["value"])

        if end:
            end_date = self.parseLogDate(end)
            if start_date > end_date:
                raise cherrypy.HTTPError(400, "Invalid date range")
        else:
            end_date = start_date

        if not by:
            raise cherrypy.HTTPError(400, "Field name to index by not specified")

        syslog.openlog(self.syslog_ident)

        index_date = start_date
        while index_date <= end_date:
            line_count = logman.index(index_date, by, match)

            syslog.syslog(
                "Indexed {} lines from {} by {}".format(
                line_count, index_date.strftime("%Y-%m-%d"), by)
            )

            index_date += one_day

        syslog.closelog()
        cherrypy.response.status = 204
