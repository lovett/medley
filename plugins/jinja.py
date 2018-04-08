# taken from https://bitbucket.org/Lawouach/cherrypy-recipes/src/d140e6da973a/web/templating/jinja2_templatin
import cherrypy
import jinja2
import http.client
import pytz
import os.path
import urllib
import os
import json
import time
import pendulum
from tzlocal import get_localzone
from cherrypy.process import plugins
from string import Template

class Plugin(plugins.SimplePlugin):
    """A WSPBus plugin that manages Jinja2 templates"""

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
            loader = loader,
            auto_reload = cherrypy.config.get("engine.autoreload.on"),
            bytecode_cache = cache
        )

        self.env.filters["datetime"] = self.datetime_filter
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

        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Called when the engine starts"""
        self.bus.log('Setting up Jinja2')
        self.bus.subscribe("lookup-template", self.get_template)

    def stop(self):
        """Called when the engine stops"""
        self.bus.log('Freeing Jinja2 resources')
        self.bus.unsubscribe("lookup-template", self.get_template)
        self.env = None

    def get_template(self, name):
        """Returns Jinja2's template by name

        Usage:
        >>> template = cherrypy.engine.publish('lookup-template', 'index.html').pop()
        """
        return self.env.get_template(name)


    def localtime_filter(self, value, format="locale"):
        """Switch a datetime to the local timezone, then format it"""

        if not value:
            return ""

        tz = self.local_timezone()

        if isinstance(value, (int, float)):
            value = pendulum.from_timestamp(value)
        else:
            value = pendulum.instance(value)

        local_value = value.in_timezone(tz)

        return self.datetime_filter(local_value, format)

    def datetime_filter(self, value, format="locale"):
        """Format a datetime as a string based on a format keyword"""

        if not value:
            return ""

        if isinstance(value, (int, float)):
            value = pendulum.from_timestamp(value)
        else:
            value = pendulum.instance(value)

        if format == "locale":
            directives = "%c"
        elif format == "date":
            directives = "%Y-%m-%d"
        elif format == "date-full":
            directives = "%A %b %d, %Y"
        elif format == "time12":
            directives = "%I:%M:%S %p"
        elif format == "time12_short":
            directives = "%I:%M %p"
        elif format == "datetime12":
            directives = "%A %b %d, %Y %I:%M %p"
        else:
            directives = format

        return value.format(directives).lstrip("0")

    def unindent_filter(self, string):
        """Remove leading whitespace from a multiline string without losing indentation"""
        if not string:
            return ""

        lines = string.split("\n")
        indents = [len(line) - len(line.lstrip(" ")) for line in lines]
        indents.remove(0)
        unindented = [line.replace(" ", "", min(indents)) for line in lines]
        return "\n".join(unindented)

    def status_message_filter(self, code):
        """Returns the standard status code message for the given integer"""
        return http.client.responses.get(int(code), "Unknown")

    def nl2br_filter(self, s):
        """Replace newlines with <br/> tags"""
        return s.replace("\n", "<br/>")

    def pluralize_filter(self, count, singular, plural=None, suffix=''):
        if not plural:
            plural = singular + "s"

        value = singular if count == 1 else plural
        return "{} {} {}".format(count, value, suffix)

    def anonymize_filter(self, url):
        anonymizer = cherrypy.engine.publish(
            "registry:first_value",
            "config:url_anonymizer",
            memorize=True
        ).pop()

        if not url.startswith("http"):
            url = "http://" + url

        if not anonymizer:
            return url

        return "{}{}".format(anonymizer, url)

    def urlencode_filter(self, value):
        return urllib.parse.quote(value)

    def local_timezone(self):
        tz = cherrypy.engine.publish(
            "registry:first_value",
            "config:timezone",
            memorize=True
        ).pop()

        if not tz:
            tz = get_localzone()

        return tz


    def ago_filter(self, unix_timestamp):
        dt = pendulum.from_timestamp(unix_timestamp)

        tz = self.local_timezone()

        return dt.in_timezone(tz).diff_for_humans()

    def yearmonth_filter(self, value):
        return value.strftime("%Y-%m")

    def json_filter(self, value):
        return json.dumps(value, sort_keys=True, indent=2)

    def websearch_filter(self, value, engine, url_only=False, target="_blank"):
        if engine is "google":
            url = "https://www.google.com#q={}"

        if engine is "bing":
            url= "https://www.bing.com/search?q={}"

        if not url:
            raise jinja2.TemplateError("Unrecognized search engine")

        url = url.format(value)

        if url_only:
            return url

        return """<a href="{}" target="{}" rel="noopener noreferer">{}</a>""".format(
            url, target, engine.capitalize()
        )

    def phonenumber_filter(self, value, as_link=False):
        """Format a US phone number as a human-readable string"""

        formats = {
             7: lambda x: "{}-{}".format(x[:3], x[3:]),
            10: lambda x: "({}) {}-{}".format(x[:3], x[3:6], x[6:]),
            11: lambda x: "({}) {}-{}".format(x[1:4], x[4:7], x[7:]),
        }

        formatter = formats.get(len(value))

        if formatter:
            formattedValue = formatter(value)
        elif "stdexten-" in value:
            formattedValue = value.replace("stdexten-", "")
        else:
            formattedValue = value

        if as_link and formattedValue != value:
            template = Template("""<a href="/phone?number=$plainNumber" rel="noreferrer">$formattedNumber</a>""")
            return template.substitute(plainNumber=value, formattedNumber=formattedValue)

        return formattedValue

    def snorql_filter(self, value):
        """Build a URL to dbpedia.org/snorql with the specified query"""

        query = self.unindent_filter(value).strip()

        encoded_query = self.urlencode_filter(query)

        return "http://dbpedia.org/snorql?query={}".format(encoded_query)

    def percentage_filter(self, value):
        if value < 1:
            return str(round(value * 100)) + "%"

        return str(value) + "%"

    @jinja2.contextfilter
    def cache_bust_filter(self, context, url):
        abs_path = cherrypy.config.get("app_root") + url

        try:
            checksum = cherrypy.engine.publish("checksum:file", abs_path).pop()
        except IndexError:
            checksum = ""
        return "{}?{}".format(url, checksum)

    @jinja2.contextfilter
    def escapejs_filter(self, context, val):
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


    def hostname_truncate_filter(self, val, length=4):
        segments = val.split(".")[::-1]
        slice = segments[:length]
        return ".".join(slice[::-1])

    def logline_with_links_filter(self, record):
        result = record["logline"]

        # ip
        link = """<a href="/visitors?query=ip+{0}"
        title="Search for visits from this address"
        rel="noreferrer">{0}</a>""".format(record["ip"])
        result = result.replace(record["ip"], link)

        return result

    def slug_filter(self, value):
        return value
