"""Render a Jinja2 template.

Based on sample code from https://bitbucket.org/Lawouach/cherrypy-recipes.
"""

import html
import http.client
from pathlib import Path
import sqlite3
import typing
import urllib
from datetime import datetime
from urllib.parse import urlparse
import json
import re
import cherrypy
import jinja2
import plugins.jinja_cache


# pylint: disable=too-many-public-methods
class Plugin(cherrypy.process.plugins.SimplePlugin):
    """A CherryPy plugin for rendering Jinja2 templates."""

    env: jinja2.Environment

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:

        self.env = jinja2.Environment(
            loader=jinja2.FunctionLoader(self.load_template),
            autoescape=True,
            auto_reload=cherrypy.config.get("engine.autoreload.on"),
            bytecode_cache=plugins.jinja_cache.Cache()
        )

        self.env.filters["date"] = self.date_filter
        self.env.filters["dateformat"] = self.dateformat_filter
        self.env.filters["ago"] = self.ago_filter
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
        self.env.filters["better_html"] = self.better_html
        self.env.filters["is_today"] = self.is_today

        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    @staticmethod
    def load_template(
            target: str
    ) -> typing.Optional[typing.Tuple[str, str, typing.Callable]]:
        """Load the specified template from the asset database.

        This is an alternative to loading templates from the
        filesystem.

        """

        template_path = Path(target)

        asset_bytes, _ = typing.cast(
            typing.Tuple[bytes, str],
            cherrypy.engine.publish(
                "assets:get",
                template_path
            ).pop()
        )

        if cherrypy.config.get("zipapp"):
            return (asset_bytes.decode(), target, lambda: True)

        mtime = 0.0
        if template_path.is_file():
            mtime = template_path.stat().st_mtime

        return (
            asset_bytes.decode(),
            target,
            lambda: template_path.stat().st_mtime == mtime
        )

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the jinja prefix
        """

        self.bus.subscribe("jinja:render", self.render)

    def render(self, template_name: str, **kwargs: typing.Any) -> bytes:
        """Populate a Jinja template."""

        template = self.env.get_template(template_name)

        data = kwargs

        data["app_name"] = cherrypy.request.script_name.lstrip("/")

        data["app_url"] = cherrypy.engine.publish(
            "url:internal"
        )

        data["page_title"] = "Medley"

        if data["app_name"]:
            data["page_title"] += f": {data['app_name'].capitalize()}"

        if "subview_title" in data:
            data["page_title"] += f": {data['subview_title']}"

        if data["app_url"]:
            data["app_url"] = data["app_url"].pop()

        cherrypy.response.headers["Content-Type"] = "text/html;charset=utf-8"

        rendered_template = typing.cast(str, template.render(**data))

        return rendered_template.encode()

    @staticmethod
    def date_filter(value: float, local: bool = False) -> datetime:
        """Convert a timestamp to a date."""

        return typing.cast(
            datetime,
            cherrypy.engine.publish(
                "clock:from_timestamp",
                value,
                local=local
            ).pop()
        )

    @staticmethod
    def dateformat_filter(dt: datetime, fmt: str) -> str:
        """Format a datetime instance to a string."""

        return typing.cast(
            str,
            cherrypy.engine.publish("clock:format", dt, fmt).pop()
        )

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

        if parsed_url.scheme not in ("http", "https"):
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
    def ago_filter(value: datetime) -> str:
        """Calculate a human-readable time delta between a date in the past
        and now.

        If the date provided as an integer or float, it is treated as
        a unix timestamp.

        """

        return typing.cast(
            str,
            cherrypy.engine.publish(
                "clock:ago",
                value
            ).pop()
        )

    @staticmethod
    def yearmonth_filter(value: datetime) -> str:
        """Format a datetime to a year-month string."""

        return typing.cast(
            str,
            cherrypy.engine.publish(
                "clock:format",
                value,
                fmt="%Y-%m"
            ).pop()
        )

    @staticmethod
    def json_filter(value: object) -> str:
        """Pretty-print a JSON value."""
        return json.dumps(value, sort_keys=True, indent=2)

    @jinja2.contextfilter
    def websearch_filter(
            self,
            context: jinja2.runtime.Context,
            value: str,
            engine: str = "",
            label: str = "",
    ) -> str:
        """Construct an offsite search URL for a term."""

        escaped_value = html.escape(value)

        if engine == "google":
            url = f"https://www.google.com/search?q={escaped_value}"

        if engine == "bing":
            url = f"https://www.bing.com/search?q={escaped_value}"

        if not url:
            raise jinja2.TemplateError("Unrecognized search engine")

        url = self.anonymize_filter(context, url)

        icon = """<svg class="icon icon-globe">
        <use xlink:href="#icon-globe"></use>
        </svg>"""

        if not label:
            label = engine.capitalize()

        result = f"""<a href="{url}"
        target="_blank" rel="noopener noreferer"
        >{icon} {label}</a>"""

        if context.eval_ctx.autoescape:
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

        if value == 1:
            return "100%"

        return str(value) + "%"

    @staticmethod
    @jinja2.contextfilter
    def cache_bust_filter(_: typing.Any, url: str) -> str:
        """Calculate a cache-aware URL to a static asset.

        A cache-aware URL contains a unique identifier in its
        querystring that changes whenever the file's content
        changes. This allows the client to cache the content far into
        the future but still pick up new versions.

        """

        asset_path = Path("apps") / url.lstrip("/")

        file_hash = cherrypy.engine.publish(
            "assets:hash",
            asset_path
        ).pop()

        return f"{url}?{file_hash}"

    @staticmethod
    @jinja2.contextfilter
    def escapejs_filter(_: typing.Any, val: str) -> str:
        """Escape special characters in JavaScript when rendered inline with
        markup.

        """

        val = val.replace("\n", "%0A")
        val = re.sub(r"\s", " ", val)

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
    @jinja2.contextfilter
    def logline_with_links_filter(
            context: jinja2.runtime.Context,
            record: sqlite3.Row
    ) -> str:
        """Add hyperlinks to a log entry."""

        result = typing.cast(str, record["logline"])

        # ip
        link = f"""<a href="/visitors?query=ip+{record['ip']}"
        title="Search for visits from this address"
        rel="noreferrer">{record['ip']}</a>"""

        result = result.replace(record["ip"], link)

        if context.eval_ctx.autoescape:
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

        return jinja2.Markup(value)

    def optional_qs_param_filter(self, value: str, key: str) -> str:
        """Return a URL querystring key-value pair if the value exists."""

        if not value:
            return ''

        encoded_value = self.urlencode_filter(value)
        return f"&{key}={encoded_value}"

    @staticmethod
    @jinja2.contextfilter
    def unescape_filter(
            context: jinja2.runtime.Context,
            value: str
    ) -> str:
        """De-entify HTML"""

        result = html.unescape(value)

        if context.eval_ctx.autoescape:
            return jinja2.Markup(result)

        return result

    @staticmethod
    @jinja2.contextfilter
    def internal_url_filter(
            context: jinja2.runtime.Context,
            value: str,
            query: typing.Dict[str, typing.Any] = None
    ) -> str:
        """Generate an application URL via the URL plugin."""

        publish_response = cherrypy.engine.publish(
            "url:internal",
            path=value,
            query=query
        )

        if not publish_response:
            return ''

        url = typing.cast(
            str,
            publish_response.pop()
        )

        if context.eval_ctx.autoescape:
            return jinja2.Markup(url)

        return url

    @staticmethod
    @jinja2.contextfilter
    def better_html(
            context: jinja2.runtime.Context,
            value: str
    ) -> str:
        """Remove undesirable markup."""

        alturl_base = cherrypy.engine.publish(
            "url:internal",
            "/alturl"
        ).pop()

        if "```" in value:
            value = re.sub(r"```([^`]+)```", r"<code>\1</code>", value)

        replacements = (
            ("<p>&#x200B;</p>", ""),
            ('<a href="/r/', f'<a href="{alturl_base}/reddit.com/r/'),
            (' ,', ', ')
        )

        result = jinja2.Markup(value)

        for before, after in replacements:
            result = result.replace(before, after)

        if context.eval_ctx.autoescape:
            return jinja2.Markup(result)

        return result

    @staticmethod
    @jinja2.contextfilter
    def is_today(
            _: jinja2.runtime.Context,
            value: datetime
    ) -> bool:
        """Deterime if a unix timestamp falls on the current date."""

        now = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        return typing.cast(
            bool,
            cherrypy.engine.publish(
                "clock:same_day",
                value,
                now
            ).pop()
        )
