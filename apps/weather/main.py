"""
Display current and upcoming weather conditions
"""

import math
import cherrypy


class Controller:
    """
    The primary controller for the application, structured for
    method-based dispatch
    """

    name = "Weather"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self):
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
            cache_key = "darksky_{}".format(latlong)
            answer = cherrypy.engine.publish(
                "cache:get",
                cache_key
            ).pop()

            if answer:
                forecasts[label] = self.shape_forecast(answer)
                continue

            latitude, longitude = latlong.split(",")
            endpoint = "https://api.darksky.net/forecast/{}/{},{}".format(
                api_key, latitude, longitude
            )

            endpoint += "?lang=en&units=us&exclude=minutely"

            answer = cherrypy.engine.publish(
                "urlfetch:get",
                endpoint,
                as_json=True,
            ).pop()

            if answer:
                forecasts[label] = self.shape_forecast(answer)

                cherrypy.engine.publish(
                    "cache:set",
                    cache_key,
                    answer,
                )

        return {
            "html": ("weather.html", {
                "app_name": self.name,
                "forecasts": forecasts
            })
        }

    @staticmethod
    def shape_forecast(forecast):
        """Reduce an API response object to wanted values"""

        result = {}

        daily_block = forecast.get("daily", {})
        days = daily_block.get("data", [{}, {}])

        today = days[0]

        currently = forecast.get("currently", {})
        hourly = forecast.get("hourly", {})

        result["current_summary"] = currently.get("summary")
        result["current_temperature"] = math.ceil(
            currently.get("temperature")
        )
        result["current_time"] = currently.get("time")
        result["current_humidity"] = currently.get("humidity", 0)

        result["summary"] = today.get("summary")
        result["temperature"] = math.ceil(today.get("temperature", 0))
        result["sunrise"] = today.get("sunriseTime")
        result["sunset"] = today.get("sunsetTime")
        result["humidity"] = currently.get("humidity", 0)

        result["high"] = math.ceil(today.get("temperatureHigh"))
        result["high_at"] = today.get("temperatureHighTime")

        result["low"] = math.ceil(today.get("temperatureLow"))
        result["low_at"] = today.get("temperatureLowTime")

        result["precip_prob"] = currently.get("precipProbability", 0) * 100
        result["precip_type"] = currently.get("precipType")

        if "data" in hourly:
            result["hourly"] = [item for item in hourly["data"]][0:24]

        return result
