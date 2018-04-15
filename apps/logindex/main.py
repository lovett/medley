"""Trigger indexing of log files."""

import os.path
import pendulum
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Log Index"

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

        cherrypy.engine.publish("logindex:enqueue", start_date, end_date)

        cherrypy.response.status = 204
