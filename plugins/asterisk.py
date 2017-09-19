import cherrypy
import os.path
import os
import socket
import pathlib
from . import mixins

class Plugin(cherrypy.process.plugins.SimplePlugin, mixins.Sqlite):
    """Interact with Asterisk via its manager interface (AMI)

    Communication occurs over a TCP socket which is returned to the caller
    from the authentication function and is expected to be passed back
    when calling other functions. The caller is also responsible for
    closing the socket.

    Failure responses are returned as boolean False."""

    sock = None

    def __init__(self, bus):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.subscribe("asterisk:set_caller_id", self.setCallerId)
        self.bus.subscribe("asterisk:get_caller_id", self.getCallerId)
        self.bus.subscribe("asterisk:blacklist", self.blacklist)
        self.bus.subscribe("asterisk:unblacklist", self.unblacklist)
        self.bus.subscribe("asterisk:is_blacklisted", self.isBlackListed)

    def stop(self):
        pass


    def authenticate(self):
        """Open an AMI connection and authenticate. Returns the opened
        socket if authentication succeeds, otherwise False"""

        registry = apps.registry.models.Registry()
        asterisk_keys = registry.search(key="asterisk:*")

        if not asterisk_keys:
            return False

        asterisk_config = {item["key"].split(":")[1] : item["value"] for index, item in enumerate(asterisk_keys)}

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.sock.connect((asterisk_config["host"], int(asterisk_config["port"])))
        except ConnectionRefusedError:
            return False

        self.sendCommand([
            "Action: login",
            "Events: off",
            "Username: {}".format(asterisk_config["username"]),
            "Secret: {}".format(asterisk_config["secret"])
        ])

        response = self.getResponse("Message")

        if not response or "Message: Authentication accepted" not in response:
            self.sock.close()
            return False

        return True


    def sendCommand(self, params):
        """Build a string of commands from the provided list and send to Asterisk.
        Takes care of newlines and encoding"""

        command = "\r\n".join(params) + "\r\n\r\n"
        self.sock.send(command.encode("UTF-8"))


    def getResponse(self, watch_for=None, return_last=False):
        """Consume a response from Asterisk until the specified watch
        word is seen. When no watch word is provided, --END COMMAND-- is used
        as the default. The response can be returned in-full, or the just the
        last line"""

        if not watch_for:
            watch_for = "--END COMMAND--"

        response = ""
        while watch_for not in response:
            response += self.sock.recv(1024).decode("UTF-8")

            if "Response: Error" in response:
                return False

        if return_last:
            return self.getLastLine(response)
        else:
            return response


    def getLastLine(self, response):
        """Returns the last data line from a response. Ignores blank lines and
        the end command line."""
        return response.strip().split("\n")[-2]


    def getValue(self, line):
        """Return the value part of a key-value line whose key is Value"""
        return line.strip().replace("Value: ", "")


    def getCallerId(self, number):
        """Look up the callerid value of the provided number"""

        self.sendCommand([
            "Action: Command",
            "Command: database get cidname {}".format(number)
        ])

        last_line = self.getResponse(return_last=True)

        if not last_line:
            return False

        if "Database entry not found" in last_line:
            return False
        else:
            return self.getValue(last_line)


    def setCallerId(self, number, value):
        """Add or update the callerid string for a number"""

        self.sendCommand([
            "Action: Command",
            "Command: database put cidname {} \"{}\"".format(number, value)
        ])

        response = self.getResponse()

        return "Updated database successfully" in response


    def blacklist(self, number):
        """Add a number to the Asterisk blacklist"""

        today = datetime.datetime.today().strftime("%Y%m%d")

        self.sendCommand([
            "Action: Command",
            "Command: database put blacklist {} {}".format(number, today)
        ])

        response = self.getResponse()

        return "Updated database successfully" in response


    def unblacklist(self, number):
        """Remove a number from the Asterisk blacklist"""

        self.sendCommand([
            "Action: Command",
            "Command: database del blacklist {}".format(number)
        ])

        response = self.getResponse()

        return "Database entry removed" in response


    def isBlackListed(self, number):
        """Look up the blacklist status of the provided number in the Asterisk
        database. Returns a datetime if found indicating when the
        number was blacklisted. Returns false if not found."""

        self.sendCommand([
            "Action: Command",
            "Command: database get blacklist {}".format(number)
        ])

        last_line = self.getResponse(return_last=True)

        if not last_line or "Database entry not found" in last_line:
            return False

        value = self.getValue(last_line)
        return datetime.datetime.strptime(value, "%Y%m%d")
