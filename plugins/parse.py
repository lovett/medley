import cherrypy
import os
from cherrypy.process import plugins
from collections import defaultdict
from pyparsing import *
import string
import os.path
from urllib.parse import urlparse
from datetime import datetime, timedelta

class Plugin(plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

        # Parsing primitives
        self.integer = Word(nums)
        self.ipv4 = Combine(self.integer + "." + self.integer + "." + self.integer + "." + self.integer)
        self.ipv6 = Word(alphanums + ":")
        self.month3 = Word(string.ascii_uppercase, string.ascii_lowercase, exact=3)
        self.tzoffset = Word("+-", nums)
        self.timestamp = Group(
            Suppress("[") +
            Combine(
                self.integer + "/" + self.month3 + "/" + self.integer +
                ":" + self.integer + ":" + self.integer + ":" + self.integer +
                " " + self.tzoffset
            ) +
            Suppress("]")
        )

        # Appengine Combined Log Grammar
        # Field order is documented at https://cloud.google.com/appengine/docs/python/logs/#Python_how_to_read_a_log
        # This is heavily based on  http://pyparsing.wikispaces.com/file/view/httpServerLogParser.py/30166005/httpServerLogParser.py
        self.appengine_grammar = (self.ipv4 | self.ipv6).setResultsName("ip") + \
        Suppress("-") + \
        ("-" | Word( alphanums + "@._")).setResultsName("auth").setParseAction(self.dashToNone) + \
        self.timestamp.setResultsName("timestamp").setParseAction(self.firstInGroup) + \
        dblQuotedString.setResultsName("cmd").setParseAction(self.requestFields) + \
        ("-" | self.integer).setResultsName("statusCode").setParseAction(self.dashToNone) + \
        ("-" | self.integer).setResultsName("numBytesSent").setParseAction(self.dashToNone) + \
        ("-" | dblQuotedString).setResultsName("referrer").setParseAction(removeQuotes, self.dashToNone) + \
        ("-" | dblQuotedString).setResultsName("agent").setParseAction(removeQuotes, self.dashToNone) + \
        Optional(dblQuotedString.setResultsName("host").setParseAction(removeQuotes)) + \
        Optional(dictOf(Word(alphanums + "_") + Suppress("="), dblQuotedString).setResultsName("extras").setParseAction(self.toDict))


    def start(self):
        self.bus.subscribe('parse:appengine', self.parseAppengine)

    def stop(self):
        pass

    def requestFields(self, s, l, t):
        """Subdivide the cmd field to isolate method, uri, query, and version

        s is the original parse string
        l is the location in the string where matching started
        t is the list of the matched tokens, packaged as a ParseResults_ object
        """
        method, uri, version = t[0].strip('"').split()

        t["method"] = method
        t["uri"] = uri
        t["query"] = None
        t["version"] = version
        if "?" in uri:
            t["uri"], t["query"] = uri.split('?', 1)


    def firstInGroup(self, s, l, t):
        """
        s is the original parse string
        l is the location in the string where matching started
        t is the list of the matched tokens, packaged as a ParseResults_ object
        """
        return t[0][0]

    def dashToNone(self, s, l, t):
        """Coerce a bare hypen to None

        s is the original parse string
        l is the location in the string where matching started
        t is the list of the matched tokens, packaged as a ParseResults_ object
        """
        return None if t[0] == "-" else t[0]

    def toDict(self, s, l, t):
        """Apply the keys and values returned by pyparsing.dictOf to the main parse result

        s is the original parse string
        l is the location in the string where matching started
        t is the list of the matched tokens, packaged as a ParseResults_ object
        """
        d = {}
        for k, v, in t[0].items():
            if v.startswith('"') and v.endswith('"'):
                d[k] = v[1:-1]
            else:
                d[k] = v

        return d

    def parseAppengine(self, val):
        fields = self.appengine_grammar.parseString(val.strip()).asDict()
        fields["timestamp"] = datetime.strptime(fields["timestamp"], "%d/%b/%Y:%H:%M:%S %z")
        fields["timestamp_unix"] = (fields["timestamp"] - datetime(1970,1,1, tzinfo=fields["timestamp"].tzinfo)) / timedelta(seconds=1)
        fields["year"] = fields["timestamp"].strftime("%Y")
        fields["month"] = fields["timestamp"].strftime("%m")
        fields["day"] = fields["timestamp"].strftime("%d")
        fields["hour"] = fields["timestamp"].strftime("%-H")

        if "referrer" in fields:
            fields["referrer_domain"] = urlparse(fields["referrer"]).netloc or None
        else:
            fields["referrer_domain"] = None

        for key, value in fields["extras"].items():
            if key == "country" and value == "ZZ":
                value = None
            elif key == "city" and value == "?":
                value = None
            elif key == "country":
                value = value.upper()
            elif key == "city":
                value = value.title()
            elif key == "region" and len(value) == 2:
                value = value.upper()

            fields[key] = value

        del fields["extras"]
        return fields
