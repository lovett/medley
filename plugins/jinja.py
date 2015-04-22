# taken from https://bitbucket.org/Lawouach/cherrypy-recipes/src/d140e6da973a/web/templating/jinja2_templating
import cherrypy
import jinja2
import http.client
import pytz
import os.path
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    """A WSPBus plugin that manages Jinja2 templates"""

    def __init__(self, bus):
        path = cherrypy.config.get("template_dir")
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(path))

        self.env.filters["datetime"] = self.datetime_filter
        self.env.filters["localtime"] = self.localtime_filter
        self.env.filters["unindent"] = self.unindent_filter
        self.env.filters["useragent"] = self.useragent_filter
        self.env.filters["status_message"] = self.status_message_filter
        self.env.filters["nl2br"] = self.nl2br_filter
        self.env.filters["pluralize"] = self.pluralize_filter
        self.env.filters["anonymize"] = self.anonymize_filter

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
        """Same as datetime_filter, but converts to the application's timezone"""
        timezone = cherrypy.config.get("timezone")

        local_value = value.astimezone(pytz.timezone(timezone))

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
            directives = "%I:%M %p"
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
        anonymizer = cherrypy.config.get("anonymizer")

        if not url.startswith("http"):
            url = "http://" + url

        if not anonymizer:
            return url
        else:
            return "{}{}".format(anonymizer, url)
