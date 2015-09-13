import sys
sys.path.append("test")

import unittest
import cherrypy
import apps.headers.main
import plugins.jinja
import cptestcase

def setup_module():
    cherrypy.config.update({
        "app_roots": [],
    })

    app_config = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.encode.on": False
        }
    }

    app = cherrypy.tree.mount(apps.headers.main.Controller(), "/", app_config)

    plugins.jinja.Plugin(cherrypy.engine).subscribe()
    cherrypy.engine.start()

def teardown_module():
    cherrypy.engine.exit()

class TestHeaders(cptestcase.BaseCherryPyTestCase):

    def test_returnsHtml(self):
        """ The application returns HTML by default """
        response = self.request("/")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/html;charset=utf-8")
        self.assertTrue("<table" in response.body)

    def test_returnsJson(self):
        """ The application returns JSON if requested """
        response = self.request("/", as_json=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        header, value = next(pair for pair in response.body if pair[0] == "Accept")
        self.assertEqual(value, "application/json")

    def test_returnsPlain(self):
        """ The application returns plain text if requested """
        response = self.request("/", as_plain=True)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/plain;charset=utf-8")
        self.assertTrue("Accept" in response.body)

    def test_noVars(self):
        """ The application takes no querystring arguments"""
        response = self.request("/?this=that")
        self.assertEqual(response.code, 404)

    def test_noParams(self):
        """ The application takes no route parameters"""
        response = self.request("/test")
        self.assertEqual(response.code, 404)

    def test_customHeader(self):
        """ The application recognizes custom headers"""
        response = self.request("/", headers={"Special_Header": "Special Value"}, as_json=True)
        print(response.body)
        header, value = next(pair for pair in response.body if pair[0] == "Special_Header")
        self.assertEqual(value, "Special Value")



if __name__ == "__main__":
    unittest.main()
