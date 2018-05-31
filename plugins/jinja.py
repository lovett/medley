"""Render a Jinja2 template.

Based on sample code from https://bitbucket.org/Lawouach/cherrypy-recipes.
"""

import http.client
import os
import os.path
import urllib
from urllib.parse import quote
import json
import re
from cherrypy.process import plugins
import cherrypy
import jinja2
import pendulum


# pylint: disable=too-many-public-methods
class Plugin(plugins.SimplePlugin):
    """A CherryPy plugin for rendering Jinja2 templates."""

    def __init__(self, bus):
        server_root = cherrypy.config.get("server_root")

        cache_dir = os.path.join(
            cherrypy.config.get("cache_dir", "cache"),
            "jinja"
        )

        try:
            os.mkdir(cache_dir)
        except PermissionError:
            raise SystemExit("Unable to create {} directory".format(cache_dir))
        except FileExistsError:
            pass

        paths = [os.path.join(server_root, "templates")]

        apps = [os.path.join(server_root, "apps", app)
                for app in os.listdir(os.path.join(server_root, "apps"))]

        apps = filter(os.path.isdir, apps)
        apps = filter(lambda x: not x.endswith("__"), apps)
        paths.extend(apps)

        loader = jinja2.FileSystemLoader(paths)

        cache = jinja2.FileSystemBytecodeCache(cache_dir, '%s.cache')

        self.env = jinja2.Environment(
            loader=loader,
            auto_reload=cherrypy.config.get("engine.autoreload.on"),
            bytecode_cache=cache
        )

        self.env.filters["dateformat"] = self.dateformat_filter
        self.env.filters["ago"] = self.ago_filter
        self.env.filters["localtime"] = self.localtime_filter
        self.env.filters["unindent"] = self.unindent_filter
        self.env.filters["status_message"] = self.status_message_filter
        self.env.filters["nl2br"] = self.nl2br_filter
        self.env.filters["pluralize"] = self.pluralize_filter
        self.env.filters["anonymize"] = self.anonymize_filter
        self.env.filters["urlencode"] = self.urlencode_filter
        self.env.filters["yearmonth"] = self.yearmonth_filter
        self.env.filters["json"] = self.json_filter
        self.env.filters["websearch"] = self.websearch_filter
        self.env.filters["phonenumber"] = self.phonenumber_filter
        self.env.filters["snorql"] = self.snorql_filter
        self.env.filters["percentage"] = self.percentage_filter
        self.env.filters["cache_bust"] = self.cache_bust_filter
        self.env.filters["escapejs"] = self.escapejs_filter
        self.env.filters["hostname_truncate"] = self.hostname_truncate_filter
        self.env.filters["logline_with_links"] = self.logline_with_links_filter
        self.env.filters["slug"] = self.slug_filter
        self.env.filters["sane_callerid"] = self.sane_callerid_filter

        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the jinja prefix
        """

        self.bus.subscribe("lookup-template", self.get_template)

    def get_template(self, name):
        """Retrieve a Jinja2 template by name."""

        return self.env.get_template(name)

    def localtime_filter(self, value, timezone=None):
        """Switch a datetime to the local timezone, then format it"""

        if not value:
            return ""

        if not timezone:
            zone = self.local_timezone()

        if isinstance(value, (int, float)):
            value = pendulum.from_timestamp(value)
        else:
            value = pendulum.instance(value)

        return value.in_timezone(zone)

    @staticmethod
    def dateformat_filter(value, format_string):
        """Format a datetime instance to a string."""

        return value.format(format_string)

    @staticmethod
    def unindent_filter(string):
        """Remove leading whitespace from a multiline string without losing
        indentation

        """
        if not string:
            return ""

        lines = string.split("\n")
        indents = [len(line) - len(line.lstrip(" ")) for line in lines]
        indents.remove(0)
        unindented = [line.replace(" ", "", min(indents)) for line in lines]
        return "\n".join(unindented)

    @staticmethod
    def status_message_filter(code):
        """Returns the standard status code message for the given integer"""
        return http.client.responses.get(int(code), "Unknown")

    @staticmethod
    def nl2br_filter(value):
        """Replace newlines with <br/> tags"""
        return value.replace("\n", "<br/>")

    @staticmethod
    def pluralize_filter(count, singular, plural=None, suffix=''):
        """Label a value with the singular or plural form of a word."""

        if not plural:
            plural = singular + "s"

        value = singular if count == 1 else plural
        return "{} {} {}".format(count, value, suffix)

    @staticmethod
    def anonymize_filter(url):
        """Prepend a URL with the URL of an anonymizer to increase referrer
        privacy.

        """
        anonymizer = cherrypy.engine.publish(
            "registry:first_value",
            "config:url_anonymizer",
            memorize=True
        ).pop()

        if not url.startswith("http"):
            url = "http://" + url

        if not anonymizer:
            return url

        return anonymizer + quote(url)

    @staticmethod
    def urlencode_filter(value):
        """Apply URL encoding to a value."""

        return urllib.parse.quote(value)

    @staticmethod
    def local_timezone():
        """Determine the timezone to be used for references to local time."""

        zone = cherrypy.engine.publish(
            "registry:first_value",
            "config:timezone",
            memorize=True
        ).pop()

        if not zone:
            zone = pendulum.now().timezone.name

        return zone

    def ago_filter(self, unix_timestamp):
        """Calculate a human-readable time delta between a timestamp and
        now.

        """

        date = pendulum.from_timestamp(unix_timestamp)

        zone = self.local_timezone()

        return date.in_timezone(zone).diff_for_humans()

    @staticmethod
    def yearmonth_filter(value):
        """Format a datetime to a year-month string."""
        return value.strftime("%Y-%m")

    @staticmethod
    def json_filter(value):
        """Pretty-print a JSON value."""
        return json.dumps(value, sort_keys=True, indent=2)

    @staticmethod
    def websearch_filter(value, engine, url_only=False, target="_blank"):
        """Construct an offsite search URL for a term."""

        if engine == "google":
            url = "https://www.google.com#q={}"

        if engine == "bing":
            url = "https://www.bing.com/search?q={}"

        if not url:
            raise jinja2.TemplateError("Unrecognized search engine")

        url = url.format(value)

        if url_only:
            return url

        template = '<a href="{}" target="{}" rel="noopener noreferer">{}</a>'
        return template.format(
            url, target, engine.capitalize()
        )

    @staticmethod
    def phonenumber_filter(value, as_link=False):
        """Format a US phone number as a human-readable string"""

        formats = {
            7: lambda x: "{}-{}".format(x[:3], x[3:]),
            10: lambda x: "({}) {}-{}".format(x[:3], x[3:6], x[6:]),
            11: lambda x: "({}) {}-{}".format(x[1:4], x[4:7], x[7:]),
        }

        formatter = formats.get(len(value))

        if formatter:
            formatted_value = formatter(value)
        elif "stdexten-" in value:
            formatted_value = value.replace("stdexten-", "")
        else:
            formatted_value = value

        if as_link and formatted_value != value:
            template = """<a href="/phone?number={}" rel="noreferrer">{}</a>"""
            return template.format(value, formatted_value)

        return formatted_value

    def snorql_filter(self, value):
        """Build a URL to dbpedia.org/snorql with the specified query"""

        query = self.unindent_filter(value).strip()

        encoded_query = self.urlencode_filter(query)

        return "http://dbpedia.org/snorql?query={}".format(encoded_query)

    @staticmethod
    def percentage_filter(value):
        """Display a value as a percentage."""

        if value < 1:
            return str(round(value * 100)) + "%"

        return str(value) + "%"

    @staticmethod
    @jinja2.contextfilter
    def cache_bust_filter(_, url):
        """Calculate a cache-aware URL to a static asset.

        A cache-aware URL is one that contains a unique identifier in
        its querystring that changes whenever the file's content
        changes. This allows the client to cache the content
        aggressively but still see new versions.

        """

        abs_path = cherrypy.config.get("app_root") + url

        try:
            checksum = cherrypy.engine.publish("checksum:file", abs_path).pop()
        except IndexError:
            checksum = ""
        return "{}?{}".format(url, checksum)

    @staticmethod
    @jinja2.contextfilter
    def escapejs_filter(_, val):
        """Escape special characters in JavaScript when rendered inline with
        markup.

        """

        return str(val).translate({
            ord('\\'): '\\u005C',
            ord('\''): '\\u0027',
            ord('"'): '\\u0022',
            ord('>'): '\\u003E',
            ord('<'): '\\u003C',
            ord('&'): '\\u0026',
            ord('='): '\\u003D',
            ord('-'): '\\u002D',
            ord(';'): '\\u003B',
            ord('`'): '\\u0060',
            ord('\u2028'): '\\u2028',
            ord('\u2029'): '\\u2029'
        })

    @staticmethod
    def hostname_truncate_filter(val, length=4):
        """Slice a hostname by segment, avoiding awkward cutoffs."""

        segments = val.split(".")[::-1]
        segment_slice = segments[:length]
        return ".".join(segment_slice[::-1])

    @staticmethod
    def logline_with_links_filter(record):
        """Add hyperlinks to a log entry."""

        result = record["logline"]

        # ip
        link = """<a href="/visitors?query=ip+{0}"
        title="Search for visits from this address"
        rel="noreferrer">{0}</a>""".format(record["ip"])

        result = result.replace(record["ip"], link)

        return result

    @staticmethod
    def slug_filter(value):
        """Reduce a string to a URL-friendly, alphanumeric form."""

        slug = value.lower()

        return re.sub(r"\s+", "-", slug)

    @staticmethod
    def sane_callerid_filter(value, default="unknown caller"):
        """Prevent Google Voice callerid strings from being displayed.

        Example: +12223334444@voice.google.com/srvenc-abc123/def456/

        """

        if "@voice.google.com" in value:
            return default

        return value
