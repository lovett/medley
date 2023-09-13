"""Test suite for the reddit plugin."""

from unittest.mock import Mock, patch, DEFAULT
from typing import Any
import cherrypy
import plugins.reddit
from testing.assertions import Subscriber
from resources.url import Url


class TestReddit(Subscriber):

    def setUp(self) -> None:
        self.plugin = plugins.reddit.Plugin(cherrypy.engine)

    @patch("cherrypy.engine.subscribe")
    def test_subscribe(self, subscribe_mock: Mock) -> None:
        """Subscriptions are prefixed consistently."""

        self.plugin.start()
        self.assert_prefixes(subscribe_mock, ("reddit",))

    @patch("cherrypy.engine.publish")
    def test_render_index(self, publish_mock: Mock) -> None:
        """The index renderer is invoked when viewing a subreddit."""
        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "urlfetch:precache":
                return [True]
            return DEFAULT

        publish_mock.side_effect = side_effect

        self.plugin.render_index = Mock(  # type: ignore
            return_value=b''
        )

        url = Url("https://reddit.com.example.com/r/hello")
        kwargs = {"hello_index": "world"}
        self.plugin.render(url, **kwargs)

        calls = self.plugin.render_index.call_args_list

        self.assertEqual(1, len(calls))
        self.assertEqual(kwargs, calls[0][1])

    @patch("cherrypy.engine.publish")
    def test_render_story(self, publish_mock: Mock) -> None:
        """The story renderer is invoked when viewing a story."""

        def side_effect(*args: str, **_: str) -> Any:
            if args[0] == "urlfetch:precache":
                return [True]
            return DEFAULT

        publish_mock.side_effect = side_effect

        self.plugin.render_story = Mock(  # type: ignore
            return_value=b''
        )

        url = Url("https://reddit.com.example.com/r/hello/comments")
        kwargs = {"hello_story": "world"}
        self.plugin.render(url, **kwargs)

        calls = self.plugin.render_story.call_args_list

        self.assertEqual(1, len(calls))
        self.assertEqual(kwargs, calls[0][1])
