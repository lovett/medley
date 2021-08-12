"""API interaction with openweathermap.org."""

import typing
from collections import defaultdict
import cherrypy

Forecast = typing.Dict[str, typing.Any]
Config = typing.Dict[str, typing.Any]


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """Make requests to the OpenWeather OneCall API."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the weather prefix."""

        self.bus.subscribe("weather:forecast", self.get_forecast)
        self.bus.subscribe("weather:config", self.get_config)

    @staticmethod
    def get_config(latitude: str, longitude: str) -> Config:
        """Load the application configuration."""

        config: Config = cherrypy.engine.publish(
            "registry:search:dict",
            "weather:*",
            key_slice=1
        ).pop()

        config["locations"] = tuple(
            tuple(value.split(",", 2))
            for key, value in config.items()
            if key.startswith("latlong")
        )

        location_name = ""
        if not latitude and not longitude:
            latitude, longitude, location_name = config.get(
                "latlong:default", ""
            ).split(",", 2)

        if not location_name:
            location_name = next((
                location[2]
                for location in config["locations"]
                if location[0] == latitude
                and location[1] == longitude
            ), "")

        config["latitude"] = latitude
        config["longitude"] = longitude
        config["location_name"] = location_name

        return config

    def get_forecast(self, config: Config) -> Forecast:
        """Request current weather data from OpenWeather."""

        latitude = config.get("latitude")
        longitude = config.get("longitude")
        api_key = config.get("openweather_api_key")

        api_response = cherrypy.engine.publish(
            "urlfetch:get",
            "https://api.openweathermap.org/data/2.5/onecall",
            params={
                "lat": latitude,
                "lon": longitude,
                "exclude": "minutely",
                "units": "imperial",
                "appid": api_key,
            },
            as_json=True,
            cache_lifespan=600
        ).pop()

        return self.shape_forecast(api_response)

    @staticmethod
    def shape_forecast(forecast: Forecast) -> Forecast:
        """Reduce an API response object to wanted values"""

        result: Forecast = defaultdict()

        daily = forecast.get("daily", [])
        hourly = forecast.get("hourly", [])
        currently = forecast.get("current", {})

        now = cherrypy.engine.publish(
            "clock:now",
            local=True
        ).pop()

        end_hour_index = 24 - now.hour
        result["currently"] = currently
        result["hourly"] = hourly[0:end_hour_index]

        hourly_tomorrow = hourly[end_hour_index:end_hour_index+24]
        result["hourly_tomorrow"] = hourly_tomorrow[6:13]
        result["today"] = daily[0]
        result["upcoming"] = daily[1:]

        result["currently"]["weather_groups"] = [
            item.get("main").lower()
            for item
            in currently["weather"]
        ]

        result["currently"]["weather_description"] = ". ".join([
            item.get("description").capitalize()
            for item
            in currently["weather"]
        ])

        result["alerts"] = []

        if forecast.get("alerts"):
            blacklist = cherrypy.engine.publish(
                "registry:search:valuelist",
                "weather:alerts:blacklist"
            ).pop()

            for alert in forecast.get("alerts", []):
                if alert["event"] in blacklist:
                    continue

                for key in ["start", "end"]:
                    alert[key] = cherrypy.engine.publish(
                        "clock:from_timestamp",
                        alert[key],
                        True
                    ).pop()

                alert["description"] = alert["description"].lstrip("...")
                alert["description"] = alert["description"].split("*")

                result["alerts"].append(alert)

        return result
