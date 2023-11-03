"""API interaction with openweathermap.org."""

import re
from datetime import datetime
from typing import Any
from typing import Dict
from typing import cast
from collections import defaultdict
import cherrypy

Forecast = Dict[str, Any]
Config = Dict[str, Any]


class Plugin(cherrypy.process.plugins.SimplePlugin):
    """Make requests to the OpenWeather OneCall API."""

    def __init__(self, bus: cherrypy.process.wspbus.Bus) -> None:
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)

    @staticmethod
    def setup() -> None:
        """Start a recurring timer to prefetch weather forecasts.

        This is the one-time call that starts the timer. Further calls
        will occur recursively from prefetch().

        The 5-second delay provides some post-server-start breathing
        room but is otherwise not important."""

        if cherrypy.config.get("prefetch"):
            cherrypy.log("[weather] Starting prefetch")
            cherrypy.engine.publish(
                "scheduler:add",
                5,
                "weather:prefetch"
            )

    def start(self) -> None:
        """Define the CherryPy messages to listen for.

        This plugin owns the weather prefix."""

        self.bus.subscribe("server:ready", self.setup)
        self.bus.subscribe("weather:forecast", self.get_forecast)
        self.bus.subscribe("weather:prefetch", self.prefetch)
        self.bus.subscribe("weather:config", self.get_config)

    @staticmethod
    def get_config(latitude: str = "", longitude: str = "") -> Config:
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
        default_latlong = config.get("latlong:default", "")
        if not latitude and not longitude and default_latlong:
            latitude, longitude, location_name = default_latlong.split(",", 2)

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

    def prefetch(self) -> None:
        """Request forecasts from OpenWeather on a recurring basis.

        This provides a caching benefit and also provides a convenient
        place for sending notifications about alerts.

        """

        wait_interval_seconds = 3600

        if not self.can_prefetch():
            cherrypy.engine.publish(
                "scheduler:add",
                wait_interval_seconds,
                "weather:prefetch"
            )
            return

        config = self.get_config()

        if "openweather_api_key" not in config:
            return

        forecast = self.get_forecast(config)

        cached_hashes = list(cherrypy.engine.publish(
            "cache:match",
            "weather"
        ).pop())

        # Only cache alerts until the end of the day. For multi-day
        # alerts, this will result in multiple notifications which is ok.
        now = datetime.now()
        end = now.replace(hour=23, minute=59, second=59)
        cache_lifespan = (end - now).seconds

        weather_app_url = cherrypy.engine.publish(
            "app_url",
            "/weather"
        ).pop()

        for _, alert in forecast.get("alerts", {}).items():
            if alert["hash"] in cached_hashes:
                continue

            badge = ""
            if alert["icon"]:
                badge = f"{alert['icon']}.svg"

            cherrypy.engine.publish(
                "notifier:send",
                {
                    "title": alert["event"],
                    "localId": f"weather-{alert['hash']}",
                    "url": weather_app_url,
                    "group": "weather",
                    "expiresAt": f"{alert['seconds_remaining']} seconds",
                    "badge": badge
                }
            )

            cherrypy.engine.publish(
                "cache:set",
                f"weather:{alert['hash']}",
                alert["hash"],
                cache_lifespan
            )

        cherrypy.engine.publish(
            "scheduler:add",
            wait_interval_seconds,
            "weather:prefetch"
        )

    def get_forecast(self, config: Config) -> Forecast:

        """Request current weather data from OpenWeather."""

        latitude = config.get("latitude")
        longitude = config.get("longitude")
        api_key = config.get("openweather_api_key")

        api_response, _ = cherrypy.engine.publish(
            "urlfetch:get:json",
            "https://api.openweathermap.org/data/2.5/onecall",
            params={
                "lat": latitude,
                "lon": longitude,
                "exclude": "minutely",
                "units": "imperial",
                "appid": api_key,
            },
            cache_lifespan=1800
        ).pop()

        try:
            return self.shape_forecast(api_response)
        except (NameError, AttributeError):
            result: Forecast = defaultdict()
            result["unavailable"] = True
            return result

    @staticmethod
    def can_prefetch() -> bool:
        """Determine whether prefetching is allowed."""

        schedules = cherrypy.engine.publish(
            "registry:search:valuelist",
            "weather:prefetch_schedule",
            exact=True
        ).pop()

        if not schedules:
            return True

        return cherrypy.engine.publish(
            "clock:scheduled",
            schedules
        ).pop()

    @staticmethod
    def shape_forecast(forecast: Forecast) -> Forecast:
        """Reduce an API response object to wanted values"""

        result: Forecast = defaultdict()
        result["unavailable"] = False

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
        result["hourly_tomorrow"] = hourly_tomorrow[6:21]
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

        result["alerts"] = {}

        if forecast.get("alerts"):
            now_unix = cherrypy.engine.publish(
                "clock:now_unix"
            ).pop()

            blacklist = cherrypy.engine.publish(
                "registry:search:valuelist",
                "weather:alerts:blacklist"
            ).pop()

            for alert in forecast.get("alerts", []):
                event = alert["event"]
                seconds_remaining = int(alert["end"] - now_unix)

                if seconds_remaining < 0:
                    continue

                alert["seconds_remaining"] = seconds_remaining

                if event in blacklist:
                    continue

                for key in ["start", "end"]:
                    alert[key] = cherrypy.engine.publish(
                        "clock:from_timestamp",
                        alert[key],
                        True
                    ).pop()

                alert["hash"] = cherrypy.engine.publish(
                    "hasher:value",
                    event
                ).pop()

                alert["description"] = re.sub(
                    r" (\d+?)(\d\d) (AM|PM) ",
                    r" \1:\2 \3 ",
                    alert["description"]
                )

                alert["description"] = re.sub(
                    r"\n",
                    " ",
                    alert["description"]
                )

                alert["description"] = alert["description"].replace(" * ", " ")

                alert["icon"] = ""
                tags = [tag.lower() for tag in alert.get("tags", [])]
                if "flood" in tags:
                    alert["icon"] = "water"
                if "extreme temperature value" in tags:
                    alert["icon"] = "temperature"

                # For multiple alerts with the same event, prefer the one
                # that ends latest.
                if event in result["alerts"]:
                    if result["alerts"][event]["end"] > alert["end"]:
                        continue

                result["alerts"][alert["event"]] = alert

        return result
