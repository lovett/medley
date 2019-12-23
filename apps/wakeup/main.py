"""Send a Wake-on-LAN packet to a sleeping host on the local network."""

import socket
import struct
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **kwargs):
        """Display the list of hosts eligible for wakeup."""

        sent = kwargs.get('sent', False)

        hosts = cherrypy.engine.publish(
            "registry:search",
            "wakeup:*",
            key_slice=1,
            as_dict=True
        ).pop()

        registry_url = cherrypy.engine.publish(
            "url:internal",
            "/registry",
            {"key": "wakeup", "view": "add", "q": "wakeup"}
        ).pop()

        return {
            "html": ("wakeup.jinja.html", {
                "hosts": hosts,
                "registry_url": registry_url,
                "sent": sent
            })
        }

    @staticmethod
    @cherrypy.tools.encode()
    @cherrypy.tools.wants()
    def POST(*_args, **kwargs):
        """Send a WoL packet to the mac address of the specified host."""

        host = kwargs.get('host')

        if not host:
            raise cherrypy.HTTPError(400, "No host specified")

        mac_address = cherrypy.engine.publish(
            "registry:first_value",
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
            return "WoL packet sent."

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            query={"sent": 1}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)
