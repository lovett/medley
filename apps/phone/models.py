import os.path
import cherrypy
import socket
import datetime
import sqlite3
import util.sqlite_converters
import apps.registry.models

class AsteriskCdr:
    """Query an Asterisk sqlite3 CDR database."""

    conn = None
    cur = None

    def __init__(self):
        db_dir = cherrypy.config.get("database_dir")
        path = os.path.join(db_dir, "asterisk_cdr.sqlite")
        sqlite3.register_converter("naive_date", util.sqlite_converters.convert_naive_date)
        sqlite3.register_converter("duration", util.sqlite_converters.convert_duration)
        sqlite3.register_converter("clid", util.sqlite_converters.convert_callerid)
        sqlite3.register_converter("channel", util.sqlite_converters.convert_channel)

        self.conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

    def __del__(self):
        if self.conn:
            self.conn.close()

    def callCount(self, src=None):
        query = """SELECT count(*) as count FROM cdr"""

        if src is None:
            self.cur.execute(query)
            return self.cur.fetchone()[0]

        query += " WHERE src=?"
        try:
            self.cur.execute(query, (src,))
            return self.cur.fetchone()[0]
        except:
            return 0

    def callLog(self, exclude=[], offset=0, limit=50):
        count = self.callCount()

        if count == 0:
            return ([], 0)

        query = """
        SELECT calldate as "date [naive_date]", end as "end_date [naive_date]",
        duration as "duration [duration]", clid as "clid [clid]",
        channel as "abbreviated_channel [channel]",
        dstchannel as "abbreviated_dstchannel [channel]", *
        FROM cdr"""

        if exclude:
            query += " WHERE src NOT IN ({}) ".format(",".join("?" * len(exclude)))

        query += """
        ORDER BY calldate DESC
        LIMIT ? OFFSET ?"""

        params = [limit, offset]
        if exclude:
            params = exclude + params

        self.cur.execute(query, params)

        try:
            return (self.cur.fetchall(), count)
        except:
            return ([], count)

    def callHistory(self, caller, limit=0, offset=0):
        count = self.callCount(caller)

        if count == 0:
            return ([], 0)

        params = []
        query = """SELECT calldate as "date [naive_date]", duration as "duration [duration]", clid as "clid [clid]", * FROM cdr WHERE src=? ORDER BY calldate DESC"""
        params.append(caller)

        if limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        if limit > 0 and offset > 0:
            query += " OFFSET ?"
            params.append(offset)

        self.cur.execute(query, params)
        result = (self.cur.fetchall(), count)

        return result



class AsteriskManager:
    """Interact with Asterisk via its manager interface (AMI)

    Communication occurs over a TCP socket which is returned to the caller
    from the authentication function and is expected to be passed back
    when calling other functions. The caller is also responsible for
    closing the socket.

    Failure responses are returned as boolean False."""

    sock = None

    def __del__(self):
        if self.sock:
            self.sock.close()

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

        response = getResponse()

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
