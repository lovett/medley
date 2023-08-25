"""Wake-on-LAN service"""

import socket
import struct
import cherrypy


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*_args: str, **kwargs: str) -> bytes:
        """Display the list of hosts eligible for wakeup."""

        sent = bool(kwargs.get("sent", False))

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
            sent=sent
        ).pop()

    @staticmethod
    @cherrypy.tools.provides(formats=("html", "text"))
    def POST(**kwargs: str) -> bytes:
        """Send a WoL packet to the mac address of the specified host."""

        host = kwargs.get("host", "").strip()

        if not host:
            raise cherrypy.HTTPError(400, "Missing host")

        mac_address = cherrypy.engine.publish(
            "registry:first:value",
            key=f"wakeup:{host}"
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
