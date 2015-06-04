"""Helper functions for interacting with Asterisk via its manager
interface (AMI)

Communication occurs over a TCP socket which is returned to the caller
from the authentication function and is expected to be passed back
when calling other functions. The caller is also responsible for
closing the socket.

Failure responses are returned as boolean False."""

import socket
import datetime


def send_command(sock, params):
    """Build a string of commands from the provided list and send to the
    provided socket. Takes care of newlines and encoding"""
    command = "\r\n".join(params) + "\r\n\r\n"
    sock.send(command.encode("UTF-8"))


def get_response(sock, watch_for=None, return_last=False):
    """Collect values from the provided socket until the specified watch
    word is seen. When no watch word is provided, --END COMMAND-- is used
    as the default. The response can be returned in-full, or the just the
    last line"""
    if not watch_for:
        watch_for = "--END COMMAND--"

    response = ""
    while watch_for not in response:
        response += sock.recv(1024).decode("UTF-8")

        if "Response: Error" in response:
            return False

    if return_last:
        return get_last_line(response)
    else:
        return response


def authenticate(config):
    """Open an AMI connection and authenticate. Config should be a dict
    with keys username, secret, host, and port. Returns the opened
    socket if authentication succeeds, otherwise False"""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((config["host"], config["port"]))
    except ConnectionRefusedError:
        return False

    params = [
        "Action: login",
        "Events: off",
        "Username: {}".format(config["username"]),
        "Secret: {}".format(config["secret"])
    ]

    send_command(sock, params)

    response = get_response(sock, "Message")

    if not response or "Message: Authentication accepted" not in response:
        sock.close()
        return False

    return sock


def get_last_line(response):
    """Returns the last data line from a response. Ignores blank lines and
    the end command line"""
    return response.strip().split("\n")[-2]


def get_value(line):
    """Returns the value part of a key-value line with the key Value"""
    return line.strip().replace("Value: ", "")


def get_callerid(sock, number):
    """Send an AMI command to look up the callerid value of the provided
    number in the Asterisk database"""

    params = [
        "Action: Command",
        "Command: database get cidname {}".format(number)
    ]

    send_command(sock, params)

    last_line = get_response(sock, return_last=True)

    if not last_line:
        return False

    if "Database entry not found" in last_line:
        return False
    else:
        return get_value(last_line)


def get_blacklist(sock, number):
    """Send an AMI command to look up the blacklist status of the provided
    number in the Asterisk database. Returns a datetime if found
    indicating when the number was blacklisted. Returns false if not
    found"""

    params = [
        "Action: Command",
        "Command: database get blacklist {}".format(number)
    ]

    send_command(sock, params)
    last_line = get_response(sock, return_last=True)

    if not last_line:
        return False

    if "Database entry not found" in last_line:
        return False
    else:
        value = get_value(last_line)
        return datetime.datetime.strptime(value, "%Y%m%d")


def save_callerid(sock, number, value):
    """Send an AMI command to add or update a callerid string for the
    provided number"""

    params = [
        "Action: Command",
        "Command: database put cidname {} \"{}\"".format(number, value)
    ]

    send_command(sock, params)

    response = get_response(sock)

    return "Updated database successfully" in response


def save_blacklist(sock, number):
    """Send an AMI command to add the provided number to the Asterisk
    blacklist database"""

    today = datetime.datetime.today().strftime("%Y%m%d")

    params = [
        "Action: Command",
        "Command: database put blacklist {} {}".format(number, today)
    ]

    send_command(sock, params)

    response = get_response(sock)

    return "Updated database successfully" in response


def blacklist_remove(sock, number):
    """Send an AMI command to remove the provided number from the Asterisk
    blacklist database"""

    params = [
        "Action: Command",
        "Command: database del blacklist {}".format(number)
    ]

    send_command(sock, params)

    response = get_response(sock)

    return "Database entry removed" in response
