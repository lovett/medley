"""Display current and upcoming weather conditions."""

import copy
import math
from collections import defaultdict
import cherrypy
import pendulum


class Controller:
    """Dispatch application requests based on HTTP verb."""

    name = "Weather"
    exposed = True
    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self, *_args, **_kwargs):
        """Display selected parts of the most recent Darksky API query"""

        config = cherrypy.engine.publish(
            "registry:search",
            "weather:*",
        ).pop()

        try:
            api_key = next(
                item["value"]
                for item in config
                if item["key"] == "weather:darksky_key"
            )

        except StopIteration:
            raise cherrypy.HTTPError(500, "No api key")

        locations = dict(
            item["value"].split("=")
            for item in config
            if item["key"].endswith("latlong")
        )

        forecasts = {}
        for label, latlong in locations.items():
            cache_key = f"darksky_{latlong}"
            answer = cherrypy.engine.publish(
                "cache:get",
                cache_key
            ).pop()

            if answer:
                forecasts[label] = self.shape_forecast(answer)
                continue

            latitude, longitude = latlong.split(",")
            endpoint = f"https://api.darksky.net/forecast/{api_key}/"
            endpoint += f"{latitude},{longitude}"
            endpoint += "?lang=en&units=us&exclude=minutely"

            api_response = cherrypy.engine.publish(
                "urlfetch:get",
                endpoint,
                as_json=True,
            ).pop()

            if api_response:
                forecasts[label] = self.shape_forecast(api_response)

                # Cache for 1 hour.
                cherrypy.engine.publish(
                    "cache:set",
                    cache_key,
                    api_response,
                    3600
                )

        return {
            "html": ("weather.jinja.html", {
                "forecasts": forecasts
            })
        }

    @staticmethod
    def shape_forecast(forecast):
        """Reduce an API response object to wanted values"""

        result = defaultdict()

        timezone = forecast.get("timezone")

        daily_block = forecast.get("daily", {})
        days = daily_block.get("data", [{}, {}])

        today = days[0]

        currently = forecast.get("currently", {})
        hourly = forecast.get("hourly", {})

        result["current_summary"] = currently.get("summary")

        result["upcoming"] = days[1:]

        for item in result["upcoming"]:
            item["time"] = pendulum.from_timestamp(
                item.get("time"), tz=timezone
            )

            if "temperatureHigh" in item:
                item["high"] = math.ceil(item.get("temperatureHigh"))

            if "temperatureHighTime" in item:
                item["high_at"] = pendulum.from_timestamp(
                    item.get("temperatureHighTime"), tz=timezone
                )

            if "temperatureLow" in item:
                item["low"] = math.ceil(item.get("temperatureLow"))

            if "temperatureLowTime" in item:
                item["low_at"] = pendulum.from_timestamp(
                    item.get("temperatureLowTime"), tz=timezone
                )

        result["current_temperature"] = math.ceil(
            currently.get("temperature")
        )

        result["current_time"] = pendulum.from_timestamp(
            currently.get("time"), tz=timezone
        )

        result["current_humidity"] = currently.get("humidity", 0)

        result["summary"] = today.get("summary")

        result["temperature"] = math.ceil(today.get("temperature", 0))

        result["sunrise"] = pendulum.from_timestamp(
            today.get("sunriseTime"), tz=timezone
        )

        result["sunset"] = pendulum.from_timestamp(
            today.get("sunsetTime"), tz=timezone
        )

        result["humidity"] = currently.get("humidity", 0)

        result["high"] = math.ceil(today.get("temperatureHigh"))

        result["high_at"] = pendulum.from_timestamp(
            today.get("temperatureHighTime"), tz=timezone
        )

        result["low"] = math.ceil(today.get("temperatureLow"))

        result["low_at"] = pendulum.from_timestamp(
            today.get("temperatureLowTime"), tz=timezone
        )

        now = pendulum.now()
        hours_remaining_today = 24 - now.hour

        if "data" in hourly:
            result["hourly"] = []
            for hour in hourly["data"][0:hours_remaining_today]:
                hour_clone = copy.copy(hour)
                hour_clone["time"] = pendulum.from_timestamp(
                    hour_clone["time"], tz=timezone
                )

                result["hourly"].append(hour_clone)

        return result
