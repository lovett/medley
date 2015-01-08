# taken from https://bitbucket.org/Lawouach/cherrypy-recipes/src/d140e6da973a/web/templating/jinja2_templating
import cherrypy
import jinja2
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    """A WSPBus plugin that manages Jinja2 templates"""

    def __init__(self, bus, path):
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(path))

        self.env.filters["datetime"] = self.datetime_filter
        self.env.filters["unindent"] = self.unindent_filter
        self.env.filters["useragent"] = self.useragent_filter

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

    def datetime_filter(self, value, format="locale"):
        """Format a datetime as a date string based on the specified format"""
        if format == "locale":
            directives = "%c"
        elif format == "date-full":
            directives = "%A %b %d, %Y"
        elif format == "time12":
            directives = "%I:%m %p"
        else:
            directives = format
        return value.strftime(directives)

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
