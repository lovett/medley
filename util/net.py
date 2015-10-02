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

def externalIp(timeout=5):
    """ Get the current external IP via DNS-O-Matic"""

    try:
        r = requests.get("http://myip.dnsomatic.com", timeout=timeout)
        r.raise_for_status()
        return r.text
    except requests.exceptions.ConnectionError:
        raise NetException("Unable to connect to DNS-o-Matic")
    except requests.exceptions.Timeout:
        raise NetException("Connection to DNS-o-matic timed out")

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
        r = requests.post(config[0], auth=config[1:2], data=message)
        r.raise_for_status()
        return True
    except:
        return False

def getHtmlTitle(html):
    """Extract the contents of the title tag from an HTML string"""
    try:
        tree = lxml.html.fromstring(html.encode("utf-8"))
        return tree.xpath("//title/text()").pop()
    except (TypeError, IndexError, lxml.etree.XMLSyntaxError):
        return None

def getUrl(url, json=False):
    """Make a GET request for the specified URL and return its HTML as a string"""

    cherrypy.log("APP", "Requesting {}".format(url))

    try:
        r = requests.get(
            url,
            timeout=5,
            allow_redirects=True,
            headers = {
                "User-Agent": "python"
            }
        )
        r.raise_for_status()
        if json:
            return r.json()
        else:
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
        tree = lxml.html.document_fromstring(html.encode("utf-8"))
    except lxml.etree.XMLSyntaxError:
        return ""

    for el in tree.xpath("//body/script"):
        el.getparent().remove(el)

    return " ".join(tree.xpath("//body//text()"))
