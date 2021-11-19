"""Wake-on-LAN dispatcher"""

import socket
import struct
import cherrypy
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic import Field


class GetParams(BaseModel):
    """Valid request parameters for GET requests."""
    sent: bool = False


class PostParams(BaseModel):
    """Valid request parameters for POST requests."""
    host: str = Field(strip_whitespace=True)


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display the list of hosts eligible for wakeup."""

        try:
            params = GetParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        hosts = cherrypy.engine.publish(
            "registry:search:dict",
            "wakeup:*",
            key_slice=1
        ).pop()

        registry_url = cherrypy.engine.publish(
            "app_url",
            "/registry",
            {"key": "wakeup", "view": "add", "q": "wakeup"}
        ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/wakeup/wakeup.jinja.html",
            hosts=hosts,
            registry_url=registry_url,
            sent=params.sent
        ).pop()

    @staticmethod
    @cherrypy.tools.provides(formats=("text", "html"))
    def POST(*_args: str, **kwargs: str) -> bytes:
        """Send a WoL packet to the mac address of the specified host."""

        try:
            params = PostParams(**kwargs)
        except ValidationError as error:
            raise cherrypy.HTTPError(400) from error

        mac_address = cherrypy.engine.publish(
            "registry:first:value",
            key=f"wakeup:{params.host}"
        ).pop()

        if not mac_address:
            raise cherrypy.HTTPError(400, "Unrecognized host")

        octets = ('FF',) * 6 + tuple(mac_address.split(':') * 16)

        packet = b''

        # pylint: disable=no-member
        for octet in octets:
            packet += struct.pack('B', int(octet, 16))

        # pylint: disable=no-member
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_socket.sendto(packet, ('<broadcast>', 9))

        if cherrypy.request.wants == "text":
            return "WoL packet sent.".encode()

        redirect_url = cherrypy.engine.publish(
            "app_url",
            query={"sent": 1}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
