import datetime
import cherrypy
import os.path

class Controller:
    """Index log files"""

    name = "Log Index"

    exposed = True

    user_facing = False

    def parseLogDate(self, val):
        filename = os.path.splitext(val)[0]
        try:
            return datetime.datetime.strptime(filename, "%Y-%m-%d")
        except:
            raise cherrypy.HTTPError(
                400,
                "Unable to parse a date from {}".format(filename)
            )

    def POST(self, start, end=None):
        start_date = self.parseLogDate(start)
        end_date = start_date

        if end:
            end_date = self.parseLogDate(end)
            if start_date > end_date:
                raise cherrypy.HTTPError(400, "Invalid date range")

        index_date = start_date
        while index_date <= end_date:
            cherrypy.engine.publish("logindex:enqueue",index_date)
            index_date += datetime.timedelta(days=1)

        cherrypy.engine.publish("logindex:schedule_parse")

        cherrypy.response.status = 204
