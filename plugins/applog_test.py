"""Test suite for the applog plugin."""

import unittest
from unittest.mock import Mock, patch
import cherrypy
import plugins.applog
from testing.assertions import Subscriber


class TestApplog(Subscriber):
    """Tests for the applog plugin."""

    def setUp(self) -> None:
        self.plugin = plugins.applog.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefixes(subscribe_mock, ("server", "applog"))

    @patch("cherrypy.engine.publish")
    def test_add(self, publish_mock: Mock) -> None:
        """A newly-added message is queued for storage."""

        self.plugin.add("foo", "bar")

        publish_mock.assert_called_with(
            "scheduler:add",
            1,
            "applog:pull"
        )

        self.assertEqual(
            len(self.plugin.queue),
            1
        )

    def test_pull_empty_queue(self) -> None:
        """Calling pull when the queue is empty exits cleanly."""

        self.plugin.pull()

        self.assertEqual(
            len(self.plugin.queue),
            0
        )

    @patch("plugins.applog.Plugin._multi")
    def test_pull(self, db_mock: Mock) -> None:
        """Queued messages are written to storage."""

        self.plugin.add("foo", "bar")
        self.plugin.add("hello", "world")
        self.plugin.pull()

        db_mock.assert_called_once()

        self.assertTrue(
            db_mock.call_args_list[0][0],
            ("foo", "bar")
        )

        self.assertTrue(
            db_mock.call_args_list[0][0],
            ("hello", "world")
        )

        self.assertEqual(
            len(self.plugin.queue),
            0
        )

    @patch("plugins.applog.Plugin._multi")
    def test_exception_message(self, db_mock: Mock) -> None:
        """Messages can be provided as exceptions."""

        try:
            raise Exception("test")  # pylint: disable=broad-exception-raised
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.plugin.add("exception test", exc)
            self.plugin.pull()

        self.assertEqual(
            db_mock.call_args_list[0][0][0][0][1][1],
            "test"
        )


if __name__ == "__main__":
    unittest.main()
