import cherrypy
import datetime
import msgpack
import pickle
import pytz
import re
import sqlite3
import urllib
from tzlocal import get_localzone
import pendulum

class Plugin(cherrypy.process.plugins.SimplePlugin):
    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        sqlite3.register_converter("datetime", self.datetime)
        sqlite3.register_converter("binary", self.binary)
        sqlite3.register_converter("calldate_to_utc", self.calldate_to_utc)
        sqlite3.register_converter("duration", self.duration)
        sqlite3.register_converter("clid", self.callerid)
        sqlite3.register_converter("querystring", self.querystring)

    def stop(self):
        pass

    def datetime(self, s):
        s = s.decode("utf-8")
        try:
            d = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
            return pytz.utc.localize(d)
        except ValueError:
            last_colon_index = s.rindex(":")
            date = s[:last_colon_index] + s[last_colon_index + 1:]
            return datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S%z")

    def local_timezone(self):
        tz = cherrypy.engine.publish(
            "registry:first_value",
            "config:timezone",
            memorize=True
        ).pop()

        if not tz:
            tz = get_localzone()

        return tz

    def calldate_to_utc(self, s):
        """Convert a local datetime string to a UTC Pendulum instance."""

        local_tz = self.local_timezone()

        return pendulum.from_format(
            s.decode("utf-8"),
            "YYYY-MM-DD HH:mm:ss",
            tz=local_tz,
            formatter='alternative'
        ).in_timezone('utc')

    def duration(self, s):
        seconds = int(s)
        hours_label = "hour"
        minutes_label = "minute"
        seconds_label = "second"

        hours = seconds // 3600
        seconds -= hours * 3600
        if hours != 1:
            hours_label += "s"

        minutes = seconds // 60
        seconds -= minutes * 60

        if minutes != 1:
            minutes_label += "s"

        if seconds != 1:
            seconds_label += "s"

        result = []
        if hours > 0:
            result.append("{} {}".format(hours, hours_label))

        if minutes > 0:
            result.append("{} {}".format(minutes, minutes_label))

        if seconds > 0:
            result.append("{} {}".format(seconds, seconds_label))

        if len(result) == 0:
            result.append("0 {}".format(seconds_label))

        return ", ".join(result)

    def callerid(self, s):
        return re.sub(r'"(.*?)".*', r"\1", s.decode("utf-8"))

    def binary(self, blob):
        try:
            return msgpack.unpackb(blob, encoding='utf-8')
        except msgpack.exceptions.ExtraData:
            return pickle.loads(blob)

    def querystring(self, s):
        return urllib.parse.parse_qs(s.decode("utf-8"), keep_blank_values=True)
