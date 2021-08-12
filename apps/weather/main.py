"""Current and upcoming forecasts"""

import typing
import cherrypy

Forecast = typing.Dict[str, typing.Any]
Config = typing.Dict[str, typing.Any]


class Controller:
    """Dispatch application requests based on HTTP verb."""

    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(*args: str, **_kwargs: str) -> bytes:
        """Display current and upcoming weather conditions."""

        latitude = ""
        longitude = ""

        if len(args) == 1:
            latitude, longitude = args[0].split(",", 1)

        config = cherrypy.engine.publish(
            "weather:config",
            latitude,
            longitude
        ).pop()

        if "openweather_api_key" not in config:
            raise cherrypy.HTTPError(500, "No api key")

        forecast = cherrypy.engine.publish(
            "weather:forecast",
            config
        ).pop()

        edit_url = cherrypy.engine.publish(
            "url:internal",
            "/registry",
            {"q": "weather:latlong"}
        ).pop()

        return typing.cast(
            bytes,
            cherrypy.engine.publish(
                "jinja:render",
                "apps/weather/weather.jinja.html",
                forecast=forecast,
                other_locations=config["locations"],
                location_name=config["location_name"],
                edit_url=edit_url,
                subview_title=config["location_name"],
            ).pop()
        )

    def POST(self, *args: str, **kwargs: str) -> None:
        """Dispatch to a subhandler based on the URL path."""

        latitude = ""
        longitude = ""
        parts = kwargs.get("parts", '')

        if args[0] == "speak":
            try:
                latitude, longitude = args[1].split(",", 1)
            except IndexError:
                pass
            return self.speak(parts, latitude, longitude)

        raise cherrypy.HTTPError(404)

    @staticmethod
    def speak(
            parts: typing.Union[str, typing.Tuple[str, ...]],
            latitude: str,
            longitude: str
    ) -> None:
        """Present the current forecast in a format suitable for
        text-to-speech."""

        config = cherrypy.engine.publish(
            "weather:config",
            latitude,
            longitude
        ).pop()

        forecast = cherrypy.engine.publish(
            "weather:forecast",
            config
        ).pop()

        statements = []

        if parts == "all":
            parts = (
                "summary",
                "temperature",
                "humidity"
            )

        for part in parts:
            statement = ""

            if part == "summary":
                statement = forecast["currently"]["weather_description"]

            if part == "temperature":
                temp = round(forecast["currently"]["temp"])
                feel = round(forecast["currently"]["feels_like"])

                statement = "It's {} degrees".format(temp)

                if abs(temp - feel) > 5:
                    statement += " but feels like {}".format(feel)

            if part == "humidity":
                statement = "{} percent humidity".format(
                    forecast["currently"]["humidity"]
                )

            if statement:
                statements.append(statement)

        for statement in statements:
            cherrypy.engine.publish(
                "speak",
                statement
            )

        cherrypy.response.status = 204
