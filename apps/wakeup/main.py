"""Send a Wake-on-LAN packets to sleeping hosts on the local network."""

import socket
import struct
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Wakup"

    @staticmethod
    @cherrypy.tools.negotiable()
    def GET(*_args, **kwargs):
        """Display the list of hosts eligible for wakeup."""

        sent = kwargs.get('sent')

        hosts = cherrypy.engine.publish(
            "registry:search",
            "wakeup:*",
            key_slice=1,
            as_dict=True
        ).pop()

        return {
            "html": ("wakeup.jinja.html", {
                "hosts": hosts,
                "sent": sent
            })
        }

    @staticmethod
    def POST(*_args, **kwargs):
        """Send a WoL packet to the mac address of the specified host."""

        host = kwargs.get('host')

        if not host:
            raise cherrypy.HTTPError(400, "No host specified")

        mac_address = cherrypy.engine.publish(
            "registry:first_value",
            key=host,
            memorize=True
        ).pop()

        if not mac_address:
            raise cherrypy.HTTPError(400, "Unrecognized host")

        octets = ('FF',) * 6 + tuple(mac_address.split(':') * 16)

        packet = b''

        for octet in octets:
            packet += struct.pack('B', int(octet, 16))

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(packet, ('<broadcast>', 9))

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            query={"sent": 1}
        ).pop()
        raise cherrypy.HTTPRedirect(redirect_url)
