"""API interaction with openweathermap.org."""

import datetime
import typing
from collections import defaultdict
import cherrypy

Forecast = typing.Dict[str, typing.Any]
Config = typing.Dict[str, typing.Any]


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

        config = self.get_config("", "")

        if "openweather_api_key" not in config:
            return

        forecast = self.get_forecast(config)

        cached_hashes = list(cherrypy.engine.publish(
            "cache:match",
            "weather"
        ).pop())

        # Only cache alerts until the end of the day. For multi-day
        # alerts, this will result in multiple notifications which is ok.
        cache_lifespan = typing.cast(
            int,
            cherrypy.engine.publish(
                "clock:day:remaining"
            ).pop()
        )

        weather_app_url = cherrypy.engine.publish(
            "url:internal",
            "/weather"
        ).pop()

        for alert in forecast.get("alerts", []):
            if alert["hash"] in cached_hashes:
                continue

            cherrypy.engine.publish(
                "notifier:send",
                {
                    "title": alert["event"],
                    "localId": f"weather-{alert['hash']}",
                    "url": weather_app_url,
                    "deliveryStyle": "whisper",
                    "group": "weather"
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
            cache_lifespan=1800
        ).pop()

        return self.shape_forecast(api_response)

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

        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(1)
        now = datetime.datetime.now()

        for schedule in schedules:
            schedule_lines = [
                line.rstrip()
                for line in schedule.split("\n")
            ]

            for time_format in ("%I:%M %p", "%H:%M"):
                try:
                    time_range = [
                        datetime.datetime.strptime(line, time_format)
                        for line in schedule_lines
                    ]
                    break
                except ValueError:
                    return True

            start = datetime.datetime.combine(today, time_range[0].time())

            if time_range[1] < time_range[0]:
                end = datetime.datetime.combine(tomorrow, time_range[1].time())
            else:
                end = datetime.datetime.combine(today, time_range[1].time())

            if start <= now <= end:
                return True

        return False

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
            now_unix = cherrypy.engine.publish(
                "clock:now_unix"
            ).pop()

            blacklist = cherrypy.engine.publish(
                "registry:search:valuelist",
                "weather:alerts:blacklist"
            ).pop()

            for alert in forecast.get("alerts", []):
                if alert["end"] < now_unix:
                    continue

                if alert["event"] in blacklist:
                    continue

                for key in ["start", "end"]:
                    alert[key] = cherrypy.engine.publish(
                        "clock:from_timestamp",
                        alert[key],
                        True
                    ).pop()

                alert["hash"] = cherrypy.engine.publish(
                    "hasher:value",
                    alert["description"]
                ).pop()

                alert["description"] = alert["description"].lstrip("...")
                alert["description"] = alert["description"].split("*")

                result["alerts"].append(alert)

        return result
