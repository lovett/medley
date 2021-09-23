"""Track food consumption."""

import datetime
import re
import typing
import cherrypy


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    def DELETE(*args: str) -> None:
        """Remove an entry from the database."""

        try:
            entry_id = int(args[0])
        except (IndexError, ValueError) as error:
            raise cherrypy.HTTPError(400) from error

        result = typing.cast(bool, cherrypy.engine.publish(
            "foodlog:remove",
            entry_id
        ).pop())

        if result:
            cherrypy.response.status = 204
            return

        raise cherrypy.HTTPError(404)

    @cherrypy.tools.provides(formats=("html",))
    def GET(self, *args: str, **kwargs: str) -> bytes:
        """Dispatch to a subhandler based on the URL path."""

        try:
            if args[0] == "new":
                return self.form(0, **kwargs)

            if args[-1] == "edit":
                entry_id = int(args[-2])
                return self.form(entry_id, **kwargs)

            if args[0] == "search":
                query = kwargs.get("q", "")
                return self.search(query, **kwargs)

            raise cherrypy.HTTPError(404)

        except ValueError as error:
            raise cherrypy.HTTPError(400) from error

        except IndexError:
            return self.index(**kwargs)

    @staticmethod
    def POST(**kwargs: str) -> None:
        """Add a new entry or update an existing one."""

        consume_date = kwargs.get("consume_date")
        consume_time = kwargs.get("consume_time")
        entry_id = kwargs.get("entry_id", 0)
        foods_eaten = kwargs.get("foods_eaten")
        overate = int(kwargs.get("overate", 0))

        consumed_on = datetime.datetime.strptime(
            f"{consume_date} {consume_time}",
            "%Y-%m-%d %H:%M",
        )

        consumed_on_utc = cherrypy.engine.publish(
            "clock:utc",
            consumed_on
        ).pop()

        result = cherrypy.engine.publish(
            "foodlog:upsert",
            entry_id,
            consumed_on=consumed_on_utc,
            foods_eaten=foods_eaten,
            overate=overate
        ).pop()

        if not result:
            raise cherrypy.HTTPError(400)

        redirect_url = cherrypy.engine.publish(
            "url:internal",
            query={"sent": 1}
        ).pop()

        raise cherrypy.HTTPRedirect(redirect_url)

    @staticmethod
    def index(*_args: str, **kwargs: str) -> bytes:
        """The application's default view."""

        offset = int(kwargs.get("offset", 0))
        limit = 20

        (entries, entry_count) = cherrypy.engine.publish(
            "foodlog:search:date",
            offset=offset
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "url:internal"
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/foodlog/foodlog-index.jinja.html",
                entries=entries,
                entry_count=entry_count,
                pagination_url=pagination_url,
                offset=offset,
                per_page=limit,
                allow_add=True
            ).pop()
        )

    @staticmethod
    def form(entry_id: int = 0, **_kwargs: str) -> bytes:
        """Display a form for adding or updating an entry."""

        entry_date = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        foods_eaten = ""
        overate = 0

        allow_delete = False
        if entry_id:
            allow_delete = True
            entry = cherrypy.engine.publish(
                "foodlog:find",
                entry_id
            ).pop()

            if not entry:
                raise cherrypy.HTTPError(404)

            entry_date = entry["consumed_on"]
            foods_eaten = entry["foods_eaten"]
            overate = entry["overate"]

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/foodlog/foodlog-form.jinja.html",
                allow_cancel=True,
                allow_add=False,
                allow_delete=allow_delete,
                entry_id=entry_id,
                entry_date=entry_date,
                foods_eaten=foods_eaten,
                overate=overate
            ).pop()
        )

    @staticmethod
    def search(query: str = "", **kwargs: str) -> bytes:
        """Display entries matching a search."""

        offset = int(kwargs.get("offset", 0))
        limit = 20

        if not query:
            redirect_url = cherrypy.engine.publish(
                "url:internal"
            ).pop()

            raise cherrypy.HTTPRedirect(redirect_url)

        query = query.lower().strip()

        publish_topic = "foodlog:search:keyword"
        search_term = query

        if re.fullmatch(r"\d{4}-\w{2}-\d{2}", query):
            publish_topic = "foodlog:search:date"
            search_term = cherrypy.engine.publish(
                "clock:from_format",
                query,
                "%Y-%m-%d"
            ).pop()

        (entries, entry_count) = cherrypy.engine.publish(
            publish_topic,
            query=search_term,
            offset=offset,
            limit=limit
        ).pop()

        pagination_url = cherrypy.engine.publish(
            "url:internal",
            "/foodlog/search",
            {"q": query}
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/foodlog/foodlog-index.jinja.html",
                entries=entries,
                entry_count=entry_count,
                query=query,
                offset=offset,
                per_page=limit,
                pagination_url=pagination_url,
                allow_cancel=True,
                allow_add=True
            ).pop()
        )
