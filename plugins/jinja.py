"""Render a Jinja2 template.

Based on sample code from https://bitbucket.org/Lawouach/cherrypy-recipes.
"""

import html
import http.client
import os
import os.path
import urllib
from urllib.parse import urlparse
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
        server_root = cherrypy.config.get("server_root", "./")

        cache_dir = os.path.join(
            cherrypy.config.get("cache_dir", "cache"),
            "jinja"
        )

        try:
            os.mkdir(cache_dir)
        except PermissionError:
            raise SystemExit(f"Unable to create {cache_dir} directory")
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
            autoescape=True,
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
        self.env.filters["autolink"] = self.autolink_filter
        self.env.filters["optional_qs_param"] = self.optional_qs_param_filter
        self.env.filters["unescape"] = self.unescape

        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the jinja prefix
        """

        self.bus.subscribe("lookup-template", self.get_template)

    def get_template(self, name):
        """Retrieve a Jinja2 template by name."""

        return self.env.get_template(name)

    @staticmethod
    def localtime_filter(value, timezone=None):
        """Switch a datetime to the local timezone, then format it"""

        if not value:
            return ""

        if not timezone:
            timezone = cherrypy.engine.publish(
                "registry:local_timezone"
            ).pop()

        if isinstance(value, (int, float)):
            value = pendulum.from_timestamp(value)
        else:
            value = pendulum.instance(value)

        return value.in_timezone(timezone)

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
    def pluralize_filter(count, singular, plural=None, suffix='',
                         number_format=',d'):
        """Label a value with the singular or plural form of a word."""

        if not plural:
            plural = singular + "s"

        value = singular if count == 1 else plural

        if suffix:
            suffix = ' ' + suffix

        return f"{count:{number_format}} {value}{suffix}"

    @staticmethod
    @jinja2.contextfilter
    def anonymize_filter(_, url):
        """Prepend an HTTP URL with the URL of the redirect app increase
        referrer privacy.

        """

        parsed_url = urlparse(url)

        if parsed_url.scheme not in ('http', 'https'):
            return url

        return cherrypy.engine.publish(
            "url:internal",
            "/redirect",
            {"u": url}
        ).pop()

    @staticmethod
    def urlencode_filter(value):
        """Apply URL encoding to a value."""

        return urllib.parse.quote(value)

    @staticmethod
    def ago_filter(value):
        """Calculate a human-readable time delta between a date in the past
        and now.

        If the date provided as an integer, it is treated as a unix timestamp.

        """

        date = value
        if isinstance(value, int):
            date = pendulum.from_timestamp(value)

        zone = cherrypy.engine.publish(
            "registry:local_timezone"
        ).pop()

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
    @jinja2.evalcontextfilter
    def websearch_filter(eval_ctx, value, engine=None, url_only=False,
                         target="_blank", with_icon=True):
        """Construct an offsite search URL for a term."""

        escaped_value = html.escape(value)

        if engine == "google":
            url = f"https://www.google.com/search?q={escaped_value}"

        if engine == "bing":
            url = f"https://www.bing.com/search?q={escaped_value}"

        if not url:
            raise jinja2.TemplateError("Unrecognized search engine")

        if url_only:
            return url

        icon = ""
        if with_icon:
            icon = """<svg class="icon icon-globe">
            <use xlink:href="#icon-globe"></use>
            </svg>"""

        result = f"""<a href="{url}"
        target="{target}" rel="noopener noreferer"
        >{icon} {engine.capitalize()}</a>"""

        if eval_ctx.autoescape:
            return jinja2.Markup(result)

        return result

    @staticmethod
    def phonenumber_filter(value, as_link=False):
        """Format a US phone number as a human-readable string"""

        formats = {
            7: lambda x: f"{x[:3]}-{x[3:]}",
            10: lambda x: f"({x[:3]}) {x[3:6]}-{x[6:]}",
            11: lambda x: f"({x[:3]}) {x[4:7]}-{x[7:]}"
        }

        formatter = formats.get(len(value))

        if formatter:
            formatted_value = formatter(value)
        elif "stdexten-" in value:
            formatted_value = value.replace("stdexten-", "")
        else:
            formatted_value = value

        href = f"/phone?number={value}"
        if as_link and formatted_value != value:
            return f'<a href="{href}" rel="noreferrer">{formatted_value}</a>'

        return formatted_value

    def snorql_filter(self, value):
        """Build a URL to dbpedia.org/snorql with the specified query"""

        query = self.unindent_filter(value).strip()

        encoded_query = self.urlencode_filter(query)

        return f"http://dbpedia.org/snorql?query={encoded_query}"

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
        return f"{url}?{checksum}"

    @staticmethod
    @jinja2.contextfilter
    def escapejs_filter(_, val):
        """Escape special characters in JavaScript when rendered inline with
        markup.

        """

        val = val.replace('\n', '%0A')
        val = re.sub(r'\s', ' ', val)

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
    @jinja2.evalcontextfilter
    def logline_with_links_filter(eval_ctx, record):
        """Add hyperlinks to a log entry."""

        result = record["logline"]

        # ip
        link = f"""<a href="/visitors?query=ip+{0}"
        title="Search for visits from this address"
        rel="noreferrer">{record['ip']}</a>"""

        result = result.replace(record["ip"], link)

        if eval_ctx.autoescape:
            return jinja2.Markup(result)

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

    def autolink_filter(self, value):
        """Convert a bare URL to a hyperlink"""

        if not value.startswith("http"):
            return value

        href = self.anonymize_filter(None, value)
        return f"""<a href="{href}"
        target="_blank" rel="noreferrer"'>{value}</a>"""

    def optional_qs_param_filter(self, value, key):
        """Return a URL querystring key-value pair if the value exists."""

        if not value:
            return ''

        encoded_value = self.urlencode_filter(value)
        return f"&{key}={encoded_value}"

    @staticmethod
    @jinja2.evalcontextfilter
    def unescape(eval_ctx, value):
        """De-entify HTML"""

        result = html.unescape(value)

        if eval_ctx.autoescape:
            return jinja2.Markup(result)

        return result
