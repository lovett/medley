"""Upcoming forecasts"""

from typing import Any
from typing import Dict
import cherrypy

Forecast = Dict[str, Any]
Config = Dict[str, Any]


class Controller:
    exposed = True
    show_on_homepage = True

    @staticmethod
    @cherrypy.tools.provides(formats=("html",))
    def GET(latlong: str = "", **_kwargs: str) -> bytes:
        """Display current and upcoming weather conditions."""

        latitude = ""
        longitude = ""
        if latlong:
            latitude, longitude = latlong.split(",", 1)

        config = cherrypy.engine.publish(
            "weather:config",
            latitude,
            longitude
        ).pop()

        app_url = cherrypy.engine.publish(
            "app_url",
        ).pop()

        redirect_url = ""

        if "openweather_api_key" not in config:
            redirect_url = cherrypy.engine.publish(
                "app_url",
                "/registry/0/new",
                {
                    "key": "weather:openweather_api_key",
                    "back": app_url
                }
            ).pop()

        if "latlong:default" not in config and not redirect_url:
            redirect_url = cherrypy.engine.publish(
                "app_url",
                "/registry/0/new",
                {
                    "key": "weather:latlong:default",
                    "back": app_url
                }
            ).pop()

        if redirect_url:
            raise cherrypy.HTTPRedirect(redirect_url)

        forecast = cherrypy.engine.publish(
            "weather:forecast",
            config
        ).pop()

        edit_url = cherrypy.engine.publish(
            "app_url",
            "/registry",
            {"q": "weather:latlong"}
        ).pop()

        if forecast["unavailable"]:
            return cherrypy.engine.publish(
                "jinja:render",
                "apps/weather/weather-unavailable.jinja.html",
                location_name=config["location_name"],
                edit_url=edit_url,
            ).pop()

        return cherrypy.engine.publish(
            "jinja:render",
            "apps/weather/weather.jinja.html",
            forecast=forecast,
            other_locations=config["locations"],
            location_name=config["location_name"],
            edit_url=edit_url,
            subview_title=config["location_name"],
        ).pop()

    def POST(
            self,
            subresource: str = "",
            latlong: str = "",
            **kwargs: str
    ) -> None:
        """Dispatch to a subhandler based on the URL path."""

        latitude = ""
        longitude = ""
        if latlong:
            latitude, longitude = latlong.split(",", 1)

        if subresource == "speak":
            parts = kwargs.get("parts", "all")
            return self.speak(parts, latitude, longitude)

        raise cherrypy.HTTPError(404)

    @staticmethod
    def speak(parts: str, latitude: str, longitude: str) -> None:
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

        speech_parts = []
        if parts == "all":
            speech_parts = [
                "summary",
                "temperature",
                "humidity",
                "alerts"
            ]

        for part in speech_parts:
            if part == "summary":
                statements.append(
                    forecast["currently"]["weather_description"]
                )

            if part == "temperature":
                temp = round(forecast["currently"]["temp"])
                feel = round(forecast["currently"]["feels_like"])

                statement = f"It's {temp} degrees"

                if abs(temp - feel) > 5:
                    statement += f" but feels like {feel}"

                statements.append(statement)

            if part == "humidity":
                statements.append(
                    f"{forecast['currently']['humidity']} percent humidity"
                )

            if part == "alerts":
                for event in forecast["alerts"].keys():
                    statements.append(f"A {event} is in effect")

        for statement in statements:
            cherrypy.engine.publish(
                "speak",
                statement
            )

        cherrypy.response.status = 204
