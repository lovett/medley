import cherrypy
import datetime
import msgpack
import pickle
import pytz
import pytz
import re
import sqlite3

class Plugin(cherrypy.process.plugins.SimplePlugin):
    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        sqlite3.register_converter("created", self.date)
        sqlite3.register_converter("binary", self.binary)
        sqlite3.register_converter("naive_date", self.naiveDate)
        sqlite3.register_converter("duration", self.duration)
        sqlite3.register_converter("clid", self.callerid)
        sqlite3.register_converter("int", self.int)

    def stop(self):
        pass

    def date(self, s):
        d = datetime.datetime.strptime(s.decode("utf-8"), "%Y-%m-%d %H:%M:%S")
        return pytz.utc.localize(d)

    def naiveDate(self, s):
        return datetime.datetime.strptime(s.decode("utf-8"), "%Y-%m-%d %H:%M:%S")

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

    def int(self, val):
        return int(val)
