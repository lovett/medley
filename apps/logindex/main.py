import sys
import time
import datetime
import os.path
import tools.negotiable
import apps.logindex.models
import util.decorator
import cherrypy

class Controller:
    """Index log files"""

    url = "/logindex"

    name = "Log Index"

    exposed = True

    user_facing = False

    def parseLogDate(self, s):
        s = s.replace(".log", "")
        try:
            return datetime.datetime.strptime(s, "%Y-%m-%d")
        except:
            raise cherrypy.HTTPError(400, "Unable to parse a date from {}".format(s))

    def POST(self, start, end=None, by="ip", match=None):
        start_time = time.time()
        one_day = datetime.timedelta(days=1)

        root = cherrypy.engine.publish("registry:first_value", "logindex:root").pop()

        if not root:
            raise cherrypy.HTTPError(500, "No log root found in registry")

        start_date = self.parseLogDate(start)
        logman = apps.logindex.models.LogManager(root)

        end_date = start_date
        if end:
            end_date = self.parseLogDate(end)
            if start_date > end_date:
                raise cherrypy.HTTPError(400, "Invalid date range")

        if not by:
            raise cherrypy.HTTPError(400, "Field name to index by not specified")

        index_date = start_date
        while index_date <= end_date:
            line_count = logman.index(index_date, by, match)

            index_date += one_day

        cherrypy.response.status = 204
