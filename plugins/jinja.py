"""Render a Jinja2 template.

Based on sample code from https://bitbucket.org/Lawouach/cherrypy-recipes.
"""

import html
import http.client
import os
import os.path
import sqlite3
import typing
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

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
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

        apps = [
            os.path.join(server_root, "apps", app)
            for app in os.listdir(os.path.join(server_root, "apps"))
            if os.path.isdir(os.path.join(server_root, "apps", app))
            and not app.startswith("__")
        ]

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
        self.env.filters["unescape"] = self.unescape_filter
        self.env.filters["internal_url"] = self.internal_url_filter

        plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the jinja prefix
        """

        self.bus.subscribe("lookup-template", self.get_template)

    def get_template(self, name: str) -> jinja2.Template:
        """Retrieve a Jinja2 template by name."""

        return self.env.get_template(name)

    @staticmethod
    def localtime_filter(
            value: pendulum.DateTime,
            timezone: str = None
    ) -> pendulum:
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
    def dateformat_filter(
            value: pendulum,
            format_string: str
    ) -> str:
        """Format a datetime instance to a string."""

        return typing.cast(str, value.format(format_string))

    @staticmethod
    def unindent_filter(string: str) -> str:
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
    def status_message_filter(code: typing.Union[str, int]) -> str:
        """Returns the standard status code message for the given integer"""
        return http.client.responses.get(int(code), "Unknown")

    @staticmethod
    def nl2br_filter(value: str) -> str:
        """Replace newlines with <br/> tags"""
        return value.replace("\n", "<br/>")

    @staticmethod
    def pluralize_filter(
            count: int,
            singular: str,
            plural: str = None,
            suffix: str = "",
            number_format: str = ',d'
    ) -> str:
        """Label a value with the singular or plural form of a word."""

        if not plural:
            plural = singular + "s"

        value = singular if count == 1 else plural

        if suffix:
            suffix = ' ' + suffix

        return f"{count:{number_format}} {value}{suffix}"

    @staticmethod
    @jinja2.contextfilter
    def anonymize_filter(
            _: typing.Any,
            url: str
    ) -> str:
        """Prepend an HTTP URL with the URL of the redirect app increase
        referrer privacy.

        """

        parsed_url = urlparse(url)

        if parsed_url.scheme not in ('http', 'https'):
            return url

        return typing.cast(
            str,
            cherrypy.engine.publish(
                "url:internal",
                "/redirect",
                {"u": url}
            ).pop()
        )

    @staticmethod
    def urlencode_filter(value: str) -> str:
        """Apply URL encoding to a value."""

        return urllib.parse.quote(value)

    @staticmethod
    def ago_filter(value: typing.Union[int, pendulum.DateTime]) -> pendulum:
        """Calculate a human-readable time delta between a date in the past
        and now.

        If the date provided as an integer, it is treated as a unix timestamp.

        """

        if isinstance(value, int):
            date = pendulum.from_timestamp(value)
        else:
            date = value

        zone = cherrypy.engine.publish(
            "registry:local_timezone"
        ).pop()

        return date.in_timezone(zone).diff_for_humans()

    @staticmethod
    def yearmonth_filter(value: pendulum) -> str:
        """Format a datetime to a year-month string."""
        return typing.cast(str, value.strftime("%Y-%m"))

    @staticmethod
    def json_filter(value: object) -> str:
        """Pretty-print a JSON value."""
        return json.dumps(value, sort_keys=True, indent=2)

    @staticmethod
    @jinja2.evalcontextfilter
    def websearch_filter(
            eval_ctx: jinja2.Environment,
            value: str,
            engine: str = "",
            url_only: bool = False,
            target: str = "_blank",
            with_icon: bool = True
    ) -> str:
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
    def phonenumber_filter(value: str, as_link: bool = False) -> str:
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

    def snorql_filter(self, value: str) -> str:
        """Build a URL to dbpedia.org/snorql with the specified query"""

        query = self.unindent_filter(value).strip()

        encoded_query = self.urlencode_filter(query)

        return f"http://dbpedia.org/snorql?query={encoded_query}"

    @staticmethod
    def percentage_filter(value: float) -> str:
        """Display a value as a percentage."""

        if value < 1:
            return str(round(value * 100)) + "%"

        return str(value) + "%"

    @staticmethod
    @jinja2.contextfilter
    def cache_bust_filter(_: typing.Any, url: str) -> str:
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
    def escapejs_filter(_: typing.Any, val: str) -> str:
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
    def hostname_truncate_filter(val: str, length: int = 4) -> str:
        """Slice a hostname by segment, avoiding awkward cutoffs."""

        segments = val.split(".")[::-1]
        segment_slice = segments[:length]
        return ".".join(segment_slice[::-1])

    @staticmethod
    @jinja2.evalcontextfilter
    def logline_with_links_filter(
            eval_ctx: jinja2.Environment,
            record: sqlite3.Row
    ) -> str:
        """Add hyperlinks to a log entry."""

        result = typing.cast(str, record["logline"])

        # ip
        link = f"""<a href="/visitors?query=ip+{record['ip']}"
        title="Search for visits from this address"
        rel="noreferrer">{record['ip']}</a>"""

        result = result.replace(record["ip"], link)

        if eval_ctx.autoescape:
            return jinja2.Markup(result)

        return result

    @staticmethod
    def slug_filter(value: str) -> str:
        """Reduce a string to a URL-friendly, alphanumeric form."""

        slug = value.lower()

        return re.sub(r"\s+", "-", slug)

    @staticmethod
    def sane_callerid_filter(
            value: str,
            default: str = "unknown caller"
    ) -> str:
        """Prevent Google Voice callerid strings from being displayed.

        Example: +12223334444@voice.google.com/srvenc-abc123/def456/

        """

        if "@voice.google.com" in value:
            return default

        return value

    @jinja2.contextfilter
    def autolink_filter(
            self,
            value: str
    ) -> str:
        """Convert a bare URL to a hyperlink"""

        links = re.findall("http[^ ]+", value)

        for link in links:
            anonymized_link = self.anonymize_filter(None, link)
            anchor = f"""<a href="{anonymized_link}"
            target="_blank" rel="noreferrer"'>{link}</a>
            """

            value = value.replace(link, anchor)

        return value

    def optional_qs_param_filter(self, value: str, key: str) -> str:
        """Return a URL querystring key-value pair if the value exists."""

        if not value:
            return ''

        encoded_value = self.urlencode_filter(value)
        return f"&{key}={encoded_value}"

    @staticmethod
    @jinja2.evalcontextfilter
    def unescape_filter(eval_ctx: jinja2.Environment, value: str) -> str:
        """De-entify HTML"""

        result = html.unescape(value)

        if eval_ctx.autoescape:
            return jinja2.Markup(result)

        return result

    @staticmethod
    @jinja2.evalcontextfilter
    def internal_url_filter(eval_ctx: jinja2.Environment,
                            value: str,
                            query: typing.Dict[str, typing.Any] = None,
                            trailing_slash: bool = False) -> str:
        """Generate an application URL via the URL plugin."""

        url = typing.cast(
            str,
            cherrypy.engine.publish(
                "url:internal",
                path=value,
                query=query,
                trailing_slash=trailing_slash
            ).pop()
        )

        if eval_ctx.autoescape:
            return jinja2.Markup(url)

        return url
