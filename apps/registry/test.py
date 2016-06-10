import cherrypy
import cptestcase
import helpers
import unittest
import responses
import apps.registry.main
import apps.registry.models
import mock
import util.cache
import tempfile
import shutil

class TestTopics(cptestcase.BaseCherryPyTestCase):
    @classmethod
    def setUpClass(cls):
        helpers.start_server(apps.registry.main.Controller)

    @classmethod
    def tearDownClass(cls):
        helpers.stop_server()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="registry-test")
        cherrypy.config["database_dir"] = self.temp_dir

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @mock.patch("apps.registry.models.Registry.find")
    @mock.patch("apps.registry.models.Registry.recent")
    @mock.patch("apps.registry.models.Registry.search")
    def test_findEntries(self, searchMock, recentMock, findMock):
        """Recent entries are returned by default"""
        response = self.request("/", uid=1)
        self.assertEqual(response.code, 200)
        self.assertTrue(findMock.called)
        self.assertFalse(recentMock.called)
        self.assertFalse(searchMock.called)

    def test_defaultView(self):
        """An invalid view returns the search view"""
        response = self.request("/", view="test")
        self.assertEqual(response.code, 200)

    @mock.patch("apps.registry.models.Registry.recent")
    @mock.patch("apps.registry.models.Registry.search")
    def test_searchEntries(self, searchMock, recentMock):
        """Registry records can be searched"""
        response = self.request("/", q="test")
        self.assertEqual(response.code, 200)
        self.assertTrue(searchMock.called)
        self.assertFalse(recentMock.called)

    @mock.patch("util.ip.facts.cache_clear")
    @mock.patch("apps.registry.models.Registry.add")
    def test_addEntry(self, addMock, cacheClearMock):
        """Records are added via a PUT which returns with a redirect"""
        cacheClearMock.return_value = True
        response = self.request("/", method="PUT", key="test", value="test1")
        self.assertEqual(response.code, 303)
        self.assertTrue(addMock.called_with("test", "test1"))
        self.assertFalse(cacheClearMock.called)

    @mock.patch("util.ip.facts.cache_clear")
    @mock.patch("apps.registry.models.Registry.add")
    def test_addEntryXHR(self, addMock, cacheClearMock):
        """Records added via XHR return the newly created id"""
        addMock.return_value = 1
        cacheClearMock.return_value = True
        response = self.request(
            "/", method="PUT", key="test", value="test1",
            as_json=True,
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(response.code, 200)
        self.assertTrue(addMock.called_with("test", "test1"))
        self.assertEqual(response.body["uid"], 1)
        self.assertFalse(cacheClearMock.called)

    @mock.patch("util.ip.facts.cache_clear")
    @mock.patch("apps.registry.models.Registry.add")
    def test_addIpEntry(self, addMock, cacheClearMock):
        """Adding an record whose key is prefixed with ip: clears the ip facts cache"""
        addMock.return_value = 1
        cacheClearMock.return_value = True
        response = self.request(
            "/", method="PUT", key="ip:test", value="test1"
        )
        self.assertTrue(cacheClearMock.called)

    @mock.patch("util.ip.facts.cache_clear")
    @mock.patch("apps.registry.models.Registry.remove")
    @mock.patch("apps.registry.models.Registry.find")
    def test_deleteEntryValidId(self, findMock, removeMock, cacheClearMock):
        """An entry can be deleted if its uid is provided"""
        findMock.return_value = ["test"]
        removeMock.return_value = 1
        cacheClearMock.return_value = True

        response = self.request(
            "/", method="DELETE", uid=1
        )
        self.assertTrue(response.code, 200)
        self.assertTrue(findMock.called)
        self.assertTrue(removeMock.called)
        self.assertFalse(cacheClearMock.called)

    @mock.patch("util.ip.facts.cache_clear")
    @mock.patch("apps.registry.models.Registry.remove")
    @mock.patch("apps.registry.models.Registry.find")
    def test_deleteEntryIpKey(self, findMock, removeMock, cacheClearMock):
        """An entry can be deleted if its uid is provided"""
        findMock.return_value = [{"key": "ip:test"}]
        removeMock.return_value = 1
        cacheClearMock.return_value = True

        response = self.request(
            "/", method="DELETE", uid=1
        )
        self.assertTrue(response.code, 200)
        self.assertTrue(findMock.called)
        self.assertTrue(removeMock.called)
        self.assertTrue(cacheClearMock.called)

    @mock.patch("util.ip.facts.cache_clear")
    @mock.patch("apps.registry.models.Registry.remove")
    @mock.patch("apps.registry.models.Registry.find")
    def test_deleteEntryInvalidId(self, findMock, removeMock, cacheClearMock):
        """Deletion fails if an invalid uid is provided"""
        findMock.return_value = []
        removeMock.return_value = 1
        cacheClearMock.return_value = True

        response = self.request(
            "/", method="DELETE", uid=1
        )
        self.assertTrue(response.code, 404)
        self.assertTrue(findMock.called)
        self.assertFalse(removeMock.called)
        self.assertFalse(cacheClearMock.called)

    @mock.patch("util.ip.facts.cache_clear")
    @mock.patch("apps.registry.models.Registry.remove")
    @mock.patch("apps.registry.models.Registry.find")
    def test_deletoinFailure(self, findMock, removeMock, cacheClearMock):
        """An error is thrown if deletion of a valid uid fails"""
        findMock.return_value = ["test"]
        removeMock.return_value = 0
        cacheClearMock.return_value = True

        response = self.request(
            "/", method="DELETE", uid=1
        )
        self.assertTrue(response.code, 400)
        self.assertTrue(findMock.called)
        self.assertTrue(removeMock.called)
        self.assertFalse(cacheClearMock.called)


if __name__ == "__main__":
    unittest.main()
