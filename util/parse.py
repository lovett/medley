from pyparsing import *
from datetime import datetime
from ua_parser import user_agent_parser
from urllib.parse import urlparse
import pytz
import string

# Primitives
# ------------------------------------------------------------------------
integer = Word(nums)
ipv4 = Combine(integer + "." + integer + "." + integer + "." + integer)
ipv6 = Word(alphanums + ":")
month3 = Word(string.ascii_uppercase, string.ascii_lowercase, exact=3)
tzoffset = Word("+-", nums)
timestamp = Group(
    Suppress("[") +
    Combine(integer + "/" + month3 + "/" + integer + ":" + integer + ":" + integer + ":" + integer + " " + tzoffset) +
    Suppress("]")
)

def getRequestFields(s, l, t):
    """
    s is the original parse string
    l is the location in the string where matching started
    t is the list of the matched tokens, packaged as a ParseResults_ object
    """
    t["method"], t["uri"], t["version"] = t[0].strip('"').split()

def getFirstInGroup(s, l, t):
    """
    s is the original parse string
    l is the location in the string where matching started
    t is the list of the matched tokens, packaged as a ParseResults_ object
    """
    return t[0][0]

def dashToNone(s, l, t):
    """Convert a bare hypen string to None

    s is the original parse string
    l is the location in the string where matching started
    t is the list of the matched tokens, packaged as a ParseResults_ object
    """
    return None if t[0] == "-" else t[0]


def assignDict(s, l, t):
    """Apply the keys and values returned by pyparsing.dictOf to the main parse result

    s is the original parse string
    l is the location in the string where matching started
    t is the list of the matched tokens, packaged as a ParseResults_ object
    """
    for k, v, in t[0].items():
        t[k] = v

# Grammars
# ------------------------------------------------------------------------

# Appengine Combined Log Grammar
# Field order is documented at https://cloud.google.com/appengine/docs/python/logs/#Python_how_to_read_a_log
# This is heavily based on  http://pyparsing.wikispaces.com/file/view/httpServerLogParser.py/30166005/httpServerLogParser.py
appengine_grammar = (ipv4 | ipv6).setResultsName("ip")
appengine_grammar += Suppress("-") # ignore the ident field
appengine_grammar += ("-" | Word( alphanums + "@._")).setResultsName("auth").setParseAction(dashToNone)
appengine_grammar += timestamp.setResultsName("timestamp").setParseAction(getFirstInGroup)
appengine_grammar += dblQuotedString.setResultsName("cmd").setParseAction(getRequestFields)
appengine_grammar += ("-" | integer).setResultsName("statusCode").setParseAction(dashToNone)
appengine_grammar += ("-" | integer).setResultsName("numBytesSent").setParseAction(dashToNone)
appengine_grammar += ("-" | dblQuotedString).setResultsName("referrer").setParseAction(removeQuotes, dashToNone)
appengine_grammar += ("-" | dblQuotedString).setResultsName("agent").setParseAction(removeQuotes, dashToNone)
appengine_grammar += dblQuotedString.setResultsName("host").setParseAction(removeQuotes)
appengine_grammar += dictOf(Word(alphas + "_") + Suppress("="), Word(alphanums + ".")).setResultsName("stats").setParseAction(assignDict)

# Parsers
# ------------------------------------------------------------------------
def appengine(line, local_timezone="US/Eastern"):
    global appengine_grammar

    fields = appengine_grammar.parseString(line)

    fields.timestamp = datetime.strptime(fields.timestamp, "%d/%b/%Y:%H:%M:%S %z")
    fields.local_timestamp = fields.timestamp.astimezone(pytz.timezone(local_timezone))

    fields.local_time = fields.local_timestamp.strftime('%I:%M:%S %p %Z').lstrip("0")
    fields.local_date = fields.local_timestamp.strftime('%Y-%m-%d')

    if fields.referrer:
        fields.referrer_domain = urlparse(fields.referrer).netloc or None
    else:
        fields.referrer_domain = None

    fields.agent = user_agent_parser.Parse(fields.agent)

    fields.line = line

    return fields
