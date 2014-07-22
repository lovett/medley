# taken from https://bitbucket.org/Lawouach/cherrypy-recipes/src/d140e6da973a/web/templating/jinja2_templating
import cherrypy
import jinja2
from cherrypy.process import plugins

class Plugin(plugins.SimplePlugin):
    """A WSPBus plugin that manages Jinja2 templates"""

    def __init__(self, bus, path):
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(path))

        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """
        Called when the engine starts.
        """
        self.bus.log('Setting up Jinja2')
        self.bus.subscribe("lookup-template", self.get_template)

    def stop(self):
        """
        Called when the engine stops.
        """
        self.bus.log('Freeing Jinja2 resources')
        self.bus.unsubscribe("lookup-template", self.get_template)
        self.env = None

    def get_template(self, name):
        """
        Returns Jinja2's template by name.

        Used as follow:
        >>> template = cherrypy.engine.publish('lookup-template', 'index.html').pop()
        """
        return self.env.get_template(name)
