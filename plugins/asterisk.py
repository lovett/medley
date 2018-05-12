"""Interact with Asterisk via its manager interface (AMI)"""

import socket
import cherrypy
import pendulum
from . import mixins


class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """A CherryPy plugin for socket-based communication with Asterisk"""

    sock = None

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        """Define the CherryPy messages to listen for.

        This plugin owns the asterisk prefix.
        """

        self.bus.subscribe("asterisk:set_caller_id", self.set_caller_id)
        self.bus.subscribe("asterisk:get_caller_id", self.get_caller_id)
        self.bus.subscribe("asterisk:blacklist", self.blacklist)
        self.bus.subscribe("asterisk:unblacklist", self.unblacklist)
        self.bus.subscribe("asterisk:is_blacklisted", self.is_blacklisted)

    def stop(self):
        """Clean up the socket used to talk to Asterisk."""

        self.disconnect()

    @staticmethod
    def get_value(line):
        """Return the value part of a key-value line whose key is Value."""

        return line.strip().replace("Value: ", "")

    @staticmethod
    def get_last_line(response):
        """Returns the last data line from a response. Ignores blank lines and
        the end command line."""

        return response.strip().split("\n")[-2]

    def authenticate(self):
        """Authenticate with a remote Asterisk server."""

        if self.sock:
            return True

        config = cherrypy.engine.publish(
            "registry:search",
            key="asterisk:*",
            as_dict=True
        ).pop()

        if not config:
            return False

        try:
            self.sock = socket.create_connection((
                config["asterisk:host"],
                int(config["asterisk:port"])
            ))
        except ConnectionRefusedError:
            return False

        self.send_command([
            "Action: login",
            "Events: off",
            "Username: {}".format(config["asterisk:username"]),
            "Secret: {}".format(config["asterisk:secret"])
        ])

        response = self.get_response("Message")

        if not response or "Message: Authentication accepted" not in response:
            self.disconnect()
            return False

        return True

    def disconnect(self):
        """End communication with the remote Asterisk server."""

        if not self.sock:
            return False

        self.sock.close()
        self.sock = None
        return True

    def send_command(self, params):
        """Build a string of commands from the provided list and send to
        Asterisk.

        Takes care of newlines and encoding.

        """

        command = "\r\n".join(params) + "\r\n\r\n"

        self.sock.send(command.encode("UTF-8"))

    def get_response(self, watch_for=None, return_last=False):
        """Consume a response from Asterisk

        Read until the specified watch word is seen. When no
        watch word is provided, --END COMMAND-- is used as the
        default. The response can be returned in-full, or the just the
        last line.

        """

        if not watch_for:
            watch_for = "--END COMMAND--"

        response = ""
        while watch_for not in response:
            response += self.sock.recv(1024).decode("UTF-8")

            if "Response: Error" in response:
                return False

        if return_last:
            return self.get_last_line(response)

        return response

    def get_caller_id(self, number):
        """Look up the callerid value for a number."""

        if not self.authenticate():
            return False

        self.send_command([
            "Action: Command",
            "Command: database get cidname {}".format(number)
        ])

        last_line = self.get_response(return_last=True)

        if not last_line:
            return None

        if "Database entry not found" in last_line:
            return None

        self.disconnect()

        return self.get_value(last_line)

    def set_caller_id(self, number, value):
        """Set the callerid value for a number."""

        if not self.authenticate():
            return False

        self.send_command([
            "Action: Command",
            "Command: database put cidname {} \"{}\"".format(number, value)
        ])

        response = self.get_response()

        self.disconnect()

        return "Updated database successfully" in response

    def blacklist(self, number):
        """Add a number to the Asterisk blacklist"""

        if not self.authenticate():
            return False

        self.send_command([
            "Action: Command",
            "Command: database put blacklist {} {}".format(
                number,
                pendulum.today().to_date_string()
            )
        ])

        response = self.get_response()

        return "Updated database successfully" in response

    def unblacklist(self, number):
        """Remove a number from the Asterisk blacklist."""

        if not self.authenticate():
            return False

        self.send_command([
            "Action: Command",
            "Command: database del blacklist {}".format(number)
        ])

        response = self.get_response()

        self.disconnect()

        return "Database entry removed" in response

    def is_blacklisted(self, number):
        """Look up the blacklist status of a number.

        Returns a pendulum instance if found indicating when the
        number was blacklisted. Returns false if not found.

        """

        if not self.authenticate():
            return False

        self.send_command([
            "Action: Command",
            "Command: database get blacklist {}".format(number)
        ])

        last_line = self.get_response(return_last=True)

        if not last_line or "Database entry not found" in last_line:
            return False

        self.disconnect()

        return pendulum.from_format(
            self.get_value(last_line),
            "YYYY-MM-DD",
            tz='local'
        )
