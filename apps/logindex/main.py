"""
Trigger indexing of log files for display by the visitors app
"""

import os.path
import pendulum
import cherrypy


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    name = "Log Index"

    exposed = True

    user_facing = False

    @staticmethod
    def parse_log_date(val):
        """Convert a date string in either date or filename format
        to a datetime.

        Date format is YYYY-mm-dd. Filename format is the same, but with
        any extension at the end, most likely ".log"

        If parsing fails, raise a 400 error."""

        filename = os.path.splitext(val)[0]

        try:
            return pendulum.strptime(filename, "%Y-%m-%d")
        except ValueError:
            raise cherrypy.HTTPError(
                400,
                "Unable to parse a date from {}".format(filename)
            )

    def POST(self, start, end=None):
        """
        Initiate log file parsing within a specified date range.
        """

        start_date = self.parse_log_date(start)
        end_date = start_date

        if end:
            end_date = self.parse_log_date(end)
            if start_date > end_date:
                raise cherrypy.HTTPError(400, "Invalid date range")

        index_date = start_date
        while index_date <= end_date:
            cherrypy.engine.publish("logindex:enqueue", index_date)
            index_date = index_date.add(days=1)

        cherrypy.engine.publish("logindex:parse")

        cherrypy.response.status = 204
