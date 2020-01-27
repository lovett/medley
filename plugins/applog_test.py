"""
Test suite for the applog plugin
"""

import unittest
import mock
import cherrypy
import plugins.applog


class TestApplog(unittest.TestCase):
    """
    Tests for the applog plugin.
    """

    def setUp(self):
        self.plugin = plugins.applog.Plugin(cherrypy.engine)

    @mock.patch("cherrypy.engine.publish")
    def test_add(self, publish_mock):
        """A newly-added message is queued for storage."""

        self.plugin.add("foo", "bar")

        self.assertEqual(
            publish_mock.call_args_list[-1].args,
            ("scheduler:add", 1, "applog:pull")
        )

        self.assertEqual(
            len(self.plugin.queue),
            1
        )

    def test_pull_empty_queue(self):
        """Calling pull when the queue is empty exits cleanly."""

        self.plugin.pull()

        self.assertEqual(
            len(self.plugin.queue),
            0
        )

    @mock.patch("plugins.applog.Plugin._insert")
    def test_pull(self, db_mock):
        """Queued messages are written to storage."""

        self.plugin.add("foo", "bar")
        self.plugin.add("hello", "world")
        self.plugin.pull()

        self.assertTrue(
            len(db_mock.call_args_list),
            1
        )

        self.assertTrue(
            db_mock.call_args_list[0].args[-1][0],
            ("foo", "bar")
        )

        self.assertTrue(
            db_mock.call_args_list[0].args[-1][1],
            ("hello", "world")
        )

        self.assertEqual(
            len(self.plugin.queue),
            0
        )

    @mock.patch("plugins.applog.Plugin._insert")
    def test_exception_message(self, db_mock):
        """Messages can be provided as exceptions."""

        try:
            raise Exception("test")
        except Exception as exception:  # pylint: disable=broad-except
            self.plugin.add("exception test", exception)
            self.plugin.pull()

        self.assertEqual(
            db_mock.call_args_list[0].args[-1][-1][-1],
            "test"
        )


if __name__ == "__main__":
    unittest.main()
