from cherrypy import Application as Application
from cherrypy.process import plugins as plugins, servers as servers
from typing import Any

def start(configfiles: Any | None = ..., daemonize: bool = ..., environment: Any | None = ..., fastcgi: bool = ..., scgi: bool = ..., pidfile: Any | None = ..., imports: Any | None = ..., cgi: bool = ...) -> None: ...
def run() -> None: ...
