# taken from https://bitbucket.org/Lawouach/cherrypy-recipes/src/d140e6da973a/web/templating/jinja2_templating
import cherrypy
import jinja2
import http.client
import pytz
import os.path
import urllib
import datetime
import os
import json
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    """A WSPBus plugin that manages Jinja2 templates"""

    def __init__(self, bus):
        app_root = cherrypy.config.get("app_root")

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

        paths = [os.path.join(app_root, "templates")]

        apps = [os.path.join(app_root, "apps", app)
                for app in os.listdir(os.path.join(app_root, "apps"))
                if not app.startswith("__")]

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
        self.env.filters["useragent"] = self.useragent_filter
        self.env.filters["status_message"] = self.status_message_filter
        self.env.filters["nl2br"] = self.nl2br_filter
        self.env.filters["pluralize"] = self.pluralize_filter
        self.env.filters["anonymize"] = self.anonymize_filter
        self.env.filters["urlencode"] = self.urlencode_filter
        self.env.filters["yearmonth"] = self.yearmonth_filter
        self.env.filters["json"] = self.json_filter
        self.env.filters["websearch"] = self.websearch_filter

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


    def localtime_filter(self, value, format="locale", timezone=None):
        """Same as datetime_filter, but converts to the application's timezone"""

        if not value:
            return ''

        if not timezone:
            timezone = cherrypy.config.get("timezone")

        if value.tzinfo:
            local_value = value.astimezone(pytz.timezone(timezone))
        else:
            local_value = pytz.timezone(timezone).localize(value)

        return self.datetime_filter(local_value, format)

    def datetime_filter(self, value, format="locale"):
        """Format a datetime as a date string based on the specified format"""

        if format == "locale":
            directives = "%c"
        elif format == "date":
            directives = "%Y-%m-%d"
        elif format == "date-full":
            directives = "%A %b %d, %Y"
        elif format == "time12":
            directives = "%I:%M:%S %p"
        elif format == "datetime12":
            directives = "%A %b %d, %Y %I:%M %p"
        else:
            directives = format

        return value.strftime(directives).lstrip("0")

    def unindent_filter(self, string):
        """Remove leading whitespace from a multiline string without losing indentation"""
        lines = string.split("\n")
        indents = [len(line) - len(line.lstrip(" ")) for line in lines]
        indents.remove(0)
        unindented = [line.replace(" ", "", min(indents)) for line in lines]
        return "\n".join(unindented)

    def useragent_filter(self, agent):
        """Format the object returned by ua-parser into a string"""
        out = ""

        if not agent:
            return ""

        if agent["device"]["family"] == "Spider":
            return agent["user_agent"]["family"]

        family = agent["user_agent"]["family"]
        version = agent["user_agent"]["major"]
        os = agent["os"]["family"]

        if family and version and os:
            return "{} {}, {}".format(family, version, os)

        return agent["string"]

    def status_message_filter(self, code):
        """Returns the standard status code message for the given integer"""
        return http.client.responses.get(int(code), "Unknown")

    def nl2br_filter(self, s):
        """Replace newlines with <br/> tags"""
        return s.replace("\n", "<br/>")

    def pluralize_filter(self, count, singular, plural):
        value = singular if count == 1 else plural
        return "{} {}".format(count, value)

    def anonymize_filter(self, url):
        anonymizer = cherrypy.config.get("url_anonymizer")

        if not url.startswith("http"):
            url = "http://" + url

        if not anonymizer:
            return url
        else:
            return "{}{}".format(anonymizer, url)

    def urlencode_filter(self, value):
        return urllib.parse.quote(value)

    def ago_filter(self, value):
        tz = cherrypy.config.get("timezone")
        timezone = pytz.timezone(tz)

        today = timezone.localize(datetime.datetime.today())

        if value.tzinfo:
            value = value.astimezone(timezone)
        else:
            value = pytz.timezone(timezone).localize(value)

        year = datetime.timedelta(days=365)
        month = datetime.timedelta(days=30)
        week = datetime.timedelta(weeks=1)
        day = datetime.timedelta(days=1)
        hour = datetime.timedelta(hours=1)
        minute = datetime.timedelta(seconds=3600)
        delta = today - value

        if delta > year:
            return "{} years".format(delta // year)

        if delta > month:
            return "{} months ago".format(delta // month)

        if delta > week:
            return "{} weeks ago".format(delta // week)

        if delta > day:
            return "{} days ago".format(delta // day)

        return "today"

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

        return """<a href="{}" target="{}" rel="noopener noreferer">Search {}</a>""".format(
            url, target, engine.capitalize()
        )
