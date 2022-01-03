"""Download files from a storage bucket."""

from enum import Enum
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError


class Service(str, Enum):
    """Valid keywords for the service parameter in POST requests."""
    NONE = ""
    GCP = "gcp"


class PostParams(BaseModel):
    """Parameters for POST requests."""
    service: Service = Service.NONE


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = False

    @staticmethod
    def POST(**kwargs: str) -> None:
        """
        Dispatch to a service-specific plugin.
        """

        try:
            params = PostParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        if params.service == Service.GCP:
            cherrypy.engine.publish(
                "scheduler:add",
                1,
                "gcp:storage:pull",
            )
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)
