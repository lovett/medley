import socket
import datetime

def sendCommand(sock, params):
    command = "\r\n".join(params) + "\r\n\r\n"
    sock.send(command.encode("UTF-8"))

def getResponse(sock, watch_for=None, last_line=False):
    if not watch_for:
        watch_for = "--END COMMAND--"

    response = ""
    while watch_for not in response:
        response += sock.recv(1024).decode("UTF-8")

        if "Response: Error" in response:
            return False

    if last_line:
        return lastLine(response)
    else:
        return response

def authenticate(config):
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

    sendCommand(sock, params)

    response = getResponse(sock, "Message")

    if "Message: Authentication accepted" not in response:
        s.close()
        return False
    else:
        return sock

def lastLine(response):
    return response.strip().split("\n")[-2]

def getValue(line):
    return line.strip().replace("Value: ", "")

def getCallerId(sock, number):
    params = [
        "Action: Command",
        "Command: database get cidname {}".format(number)
    ]

    sendCommand(sock, params)

    last_line = getResponse(sock, last_line=True)

    if not last_line:
        return False

    if "Database entry not found" in last_line:
        return False
    else:
        return getValue(last_line)

def getBlacklist(sock, number):
    params = [
        "Action: Command",
        "Command: database get blacklist {}".format(number)
    ]

    sendCommand(sock, params)
    last_line = getResponse(sock, last_line=True)

    if not last_line:
        return False

    if "Database entry not found" in last_line:
        return False
    else:
        value = getValue(last_line)
        return datetime.datetime.strptime(value, "%Y%m%d")

def saveCallerId(sock, number, value):
    params = [
        "Action: Command",
        "Command: database put cidname {} \"{}\"".format(number, value)
    ]

    sendCommand(sock, params)

    response = getResponse(sock)

    return "Updated database successfully" in response

def saveBlacklist(sock, number):
    today = datetime.datetime.today().strftime("%Y%m%d")

    params = [
        "Action: Command",
        "Command: database put blacklist {} {}".format(number, today)
    ]

    sendCommand(sock, params)

    response = getResponse(sock)

    return "Updated database successfully" in response

def blacklistRemove(sock, number):

    params = [
        "Action: Command",
        "Command: database del blacklist {}".format(number)
    ]

    sendCommand(sock, params)

    response = getResponse(sock)

    return "Database entry removed" in response
