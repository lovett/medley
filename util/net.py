import subprocess
import socket
import re
import requests
import jinja2
import smtplib
import pytz
import string
from email.mime.text import MIMEText
from datetime import datetime
from ua_parser import user_agent_parser
from urllib.parse import urlparse
from pyparsing import *

def whois(address):
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
    skip_until_blank = False
    for line in out_raw:
        line = line.strip()

        if skip_until_blank:
            if line.strip() != "":
                continue
            else:
                skip_until_blank = False

        # Skip comments
        if line.startswith(("#", "%")):
            continue

        # Skip verbose lines
        if len(line.split()) > 10:
            skip_until_blank = True
            continue

        line = re.sub(r"\s+", " ", line).strip()
        line = line.lstrip(">>>").strip("<<<")
        fields = line.split(": ", 1)

        # Skip unlabelled lines
        if len(fields) == 1:
            continue

        # Remove camel case from labels
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
        pass

def reverseLookup(ip=None):
    """Find the hostname associated with the given IP"""

    try:
        result = socket.gethostbyaddr(ip)
        return result[0]
    except:
        pass

def externalIp(timeout=3):
    """ Get the current external IP via DNS-O-Matic"""

    try:
        r = requests.get("http://myip.dnsomatic.com", timeout=timeout)
        r.raise_for_status()
        return r.text
    except:
        return None

def sendMessage(message_data, template_data):
    """Render an email template and send via SMTP"""

    loader = jinja2.FileSystemLoader(message_data["template_dir"])
    env = jinja2.Environment(loader=loader)
    template = env.get_template(message_data["template"])

    rendered_template = template.render(template_data)

    message = MIMEText(rendered_template)
    message["To"] = ", ".join(message_data["smtp"]["recipients"])
    message["Subject"] = message_data["subject"]
    message["From"] = message_data["smtp"]["sender"]

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

def sendNotification(message, config):
    r = requests.post(config["endpoint"], auth=config["auth"], data=message)
    r.raise_for_status()
    return True

def parse_appengine(line):
    # Heavily based on  http://pyparsing.wikispaces.com/file/view/httpServerLogParser.py/30166005/httpServerLogParser.py

    integer = Word(nums)
    decimal = Word(nums + ".")
    ipv4 = Combine(integer + "." + integer + "." + integer + "." + integer)
    ipv6 = Word(alphanums + ":")
    month = Word(string.ascii_uppercase, string.ascii_lowercase, exact=3)

    tzoffset = Word("+-", nums)
    timestamp = Group(Suppress("[") +
                      Combine(integer + "/" + month + "/" + integer + ":" + integer + ":" + integer + ":" + integer + " " + tzoffset) +
                      Suppress("]"))

    def getCmdFields( s, l, t ):
        t["method"], t["uri"], t["version"] = t[0].strip('"').split()

    fields = (ipv4 | ipv6).setResultsName("ip")
    fields += Suppress("-") # ignore ident
    fields += ("-" | Word( alphas+nums+"@._" )).setResultsName("auth")
    fields += timestamp.setResultsName("timestamp")
    fields += dblQuotedString.setResultsName("cmd").setParseAction(getCmdFields)
    fields += (integer | "-").setResultsName("statusCode")
    fields += (integer | "-").setResultsName("numBytesSent")
    fields += ("-" | dblQuotedString).setResultsName("referrer").setParseAction(removeQuotes)
    fields += ("-" | dblQuotedString).setResultsName("agent").setParseAction(removeQuotes)
    fields += dblQuotedString.setResultsName("domain").setParseAction(removeQuotes)
    fields += "ms=" + integer.setResultsName("ms")
    fields += "cpu_ms=" + integer.setResultsName("cpu_ms")
    fields += "cpm_usd=" + decimal.setResultsName("cpm_usd")
    #fields += "pending_msd=" + integer.setResultsName("pending_msd")
    #fields += "instance=" + Word(string.ascii_lowercase + string.digits).setResultsName("instance")
    #fields += "app_engine_release=" + decimal.setResultsName("app_engine_release")

    parsed = fields.parseString(line)

    log_date = datetime.strptime(parsed.timestamp[0], "%d/%b/%Y:%H:%M:%S %z")
    local_date = log_date.astimezone(pytz.timezone('US/Eastern'))

    if parsed.referrer == "-":
        parsed.referrer = None
        parsed.referrer_domain = None
    else:
        print(parsed.referrer)
        parsed.referrer_domain = urlparse(parsed.referrer).netloc or None

    agent = user_agent_parser.Parse(parsed.agent)

    return {
        "ip": parsed.ip,
        "date": log_date,
        "time_string": local_date.strftime('%I:%M:%S %p %Z').lstrip("0"),
        "date_string": local_date.strftime('%Y-%m-%d'),
        "method": parsed.method,
        "uri": parsed.uri,
        "status": parsed.statusCode,
        "bytes": parsed.numBytesSent,
        "referrer": parsed.referrer,
        "referrer_domain": parsed.referrer_domain,
        "agent": agent,
        "host": parsed.domain,
        "line": line
    }
