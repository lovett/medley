import subprocess
import socket
import re
import urllib3
import jinja2
from email.mime.text import MIMEText
import smtplib

def query(address):
    """Run a whois query by shelling out. The output is filtered to
    improve readability. Returns a list of key value pairs.

    Although there are some whois Python modules, none proved viable
    for Python 3.2"""

    assert address is not None
    assert len(address) > 0, "Invalid address"

    process = subprocess.Popen(["whois", address],
                               stdout=subprocess.PIPE)
    out, err = process.communicate()

    try:
        out_raw = out.decode("utf-8")
    except UnicodeDecodeError:
        out_raw = out.decode("latin-1")

    out_raw = out_raw.split("\n")

    out_filtered = []
    for line in out_raw:
        line = line.strip()

        # remove comments
        if line.startswith(("#", "%")):
            continue

        # separate label and value for non-comment lines
        line = re.sub(r"\s+", " ", line).strip()
        fields = line.split(": ", 1)

        # Discard blank lines
        if fields[0] == "":
            continue

        # Discard labelled lines with no value
        if len(fields) == 1 and ":" in fields[0]:
            continue

        # Preserve unlabelled lines
        if len(fields) == 1:
            fields.append(None)
        else:
            fields[0] = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", fields[0]).title()

        out_filtered.append(fields)

    # collapse repeated headers and comment lines
    previous = None
    out_collapsed = []
    for line in out_filtered:
        if line[1] is not None and line[0] == previous:
            out_collapsed[-1][-1] += "\n" + line[1]
        else:
            out_collapsed.append(line)
            previous = line[0]

    return out_collapsed

def resolveHost(host=None):
    """Resolve a hostname to its IP address"""

    try:
        result = socket.gethostbyname_ex(host)
        return result[2][0]
    except:
        return None

def reverseLookup(ip=None):
    """Find the hostname associated with the given IP"""

    try:
        result = socket.gethostbyaddr(ip)
        return result[0]
    except:
        return None

def externalIp():
    """ Get the current external IP via DNS-O-Matic"""

    http = urllib3.PoolManager()
    try:
        response = http.request("GET", "http://myip.dnsomatic.com/")
        if response.status == 200:
            return response.data.decode("UTF-8")
        else:
            return None
    except:
        return None

def sendMessage(message_data, template_data, debug=False):
    """Compose an email message from a Jinja template and send via
    localhost SMTP"""

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(message_data["template_dir"]))
    template = env.get_template(message_data["template"])

    rendered_template = template.render(template_data)

    message = MIMEText(rendered_template)
    message["To"] = ", ".join(message_data["smtp"]["recipients"])
    message["Subject"] = message_data["subject"]
    message["From"] = message_data["smtp"]["sender"]

    if debug:
        return message.as_string()

    mailserver = smtplib.SMTP(message_data["smtp"]["host"],
                              message_data["smtp"]["port"])
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login(message_data["smtp"]["username"],
                   message_data["smtp"]["password"])

    mailserver.sendmail(message_data["smtp"]["sender"],
                        ", ".join(message_data["smtp"]["recipients"]),
                        message.as_string())
