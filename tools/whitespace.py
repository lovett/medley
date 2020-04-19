"""Normalize the whitespace of request parameters."""
import cherrypy


class Tool(cherrypy.Tool):
    """A custom Cherrypy tool to normalize request parameter whitespace."""

    def __init__(self) -> None:
        cherrypy.Tool.__init__(
            self,
            'before_handler',
            self.normalize
        )

    @staticmethod
    def normalize() -> None:
        """Perform whitespace normalization."""

        for key, value in cherrypy.request.params.items():
            if not value:
                continue

            if isinstance(cherrypy.request.params[key], list):
                for index, val in enumerate(cherrypy.request.params[key]):
                    if not isinstance(val, str):
                        continue

                    cherrypy.request.params[key][index] = val.replace(
                        "\r", ""
                    ).strip()

            if isinstance(cherrypy.request.params[key], str):
                cherrypy.request.params[key] = value.replace("\r", "").strip()
