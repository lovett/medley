# taken from https://bitbucket.org/Lawouach/cherrypy-recipes/src/d140e6da973a/web/templating/jinja2_templating
import cherrypy

class Tool(cherrypy.Tool):
    def __init__(self):
        cherrypy.Tool.__init__(self, 'before_finalize',
                               self._render,
                               priority=10)

    def _render(self, template=None, debug=False):
        """
        Applied once your page handler has been called. It
        looks up the template from the various template directories
        defined in the Jinja2 plugin then renders it with
        whatever dictionary the page handler returned.
        """

        # retrieve the data returned by the handler
        data = cherrypy.response.body or {}

        template = cherrypy.engine.publish("lookup-template", template).pop()

        if template and isinstance(data, dict):
            cherrypy.response.body = template.render(**data).encode('UTF-8')
