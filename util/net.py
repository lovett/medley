import subprocess
import socket
import re
import shutil
import requests
import jinja2
import smtplib
import lxml.html
import lxml.etree
import cherrypy
from email.mime.text import MIMEText

class NetException (Exception):
    pass

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

def externalIp(timeout=5):
    """ Get the current external IP via DNS-O-Matic"""

    try:
        r = requests.get("http://myip.dnsomatic.com", timeout=timeout)
        r.raise_for_status()
        return r.text
    except requests.exceptions.HTTPError:
        raise NetException("DNS-o-Matic query failed")

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
    try:
        r = requests.post(config["endpoint"], auth=config["auth"], data=message)
        r.raise_for_status()
        return True
    except:
        return False

def getHtmlTitle(html):
    """Extract the contents of the title tag from an HTML string"""
    try:
        tree = lxml.html.fromstring(html)
        return tree.xpath("//title/text()").pop()
    except (TypeError, IndexError, lxml.etree.XMLSyntaxError):
        return None

def reduceHtmlTitle(title):
    """Remove site identifiers and noise from the title of an HTML document"""
    title = title or ""
    for char in "|-:·":
        separator = " {} ".format(char)
        if separator in title:
            segments = title.split(separator)
            return max(segments, key=len)
    return title

def getUrl(url):
    """Make a GET request for the specified URL and return its HTML as a string"""

    cherrypy.log("APP", "Requesting {}".format(url))

    try:
        r = requests.get(url, timeout=5, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except requests.exceptions.HTTPError as e:
        raise NetException(e)

def saveUrl(url, destination):
    """Download a URL, saving the response body to the filesystem"""

    cherrypy.log("APP", "Requesting {}".format(url))

    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        raise NetException("URL download failed")

    if r.status_code == 200:
        with open(destination, "wb") as f:
            shutil.copyfileobj(r.raw, f)

def htmlToText(html):
    """Reduce an HTML document to the text nodes of the body tag"""
    try:
        tree = lxml.html.document_fromstring(html)
    except lxml.etree.XMLSyntaxError:
        return ""

    for el in tree.xpath("//body/script"):
        el.getparent().remove(el)

    return " ".join(tree.xpath("//body//text()"))
