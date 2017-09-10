import cherrypy
import math

class Controller:
    """The current forecast"""

    url = "/weather"

    name = "Weather"

    exposed = True

    user_facing = True

    @cherrypy.tools.negotiable()
    def GET(self):

        config = cherrypy.engine.publish(
            "registry:search",
            "weather:*",
        ).pop()

        try:
            api_key = next(item["value"] for item in config if item["key"] == "weather:darksky_key")
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
                forecasts[label] = self.shapeForecast(answer)
                continue

            latitude, longitude = latlong.split(",")
            endpoint = "https://api.darksky.net/forecast/{}/{},{}?lang=en&units=us&exclude=minutely".format(
                api_key, latitude, longitude
            )

            answer = cherrypy.engine.publish(
                "urlfetch:get",
                endpoint,
                as_json=True,
            ).pop()

            if answer:
                forecasts[label] = self.shapeForecast(answer)

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

    def shapeForecast(self, forecast):
        """Reduce an API response object to wanted values"""

        result = {}

        daily_block = forecast.get("daily", {})
        days = daily_block.get("data", [{}, {}])

        today = days[0]
        tomorrow = days[1]

        current_block = forecast.get("currently", {})
        hourly_block = forecast.get("hourly", {})

        result["current_summary"] = current_block.get("summary")
        result["current_temperature"] = math.ceil(current_block.get("temperature"))
        result["current_time"] = current_block.get("time")
        result["current_humidity"] = current_block.get("humidity", 0)

        result["summary"] = today.get("summary")
        result["temperature"] = math.ceil(today.get("temperature", 0))
        result["sunrise"] = today.get("sunriseTime")
        result["sunset"] = today.get("sunsetTime")
        result["humidity"] = current_block.get("humidity", 0)

        result["high"] = math.ceil(today.get("temperatureHigh"))
        result["high_at"] = today.get("temperatureHighTime")

        result["low"] = math.ceil(today.get("temperatureLow"))
        result["low_at"] = today.get("temperatureLowTime")

        result["liklihood_of_precipitation"] = current_block.get("precipProbability", 0) * 100
        result["precipitation_type"] = current_block.get("precipType")

        if "data" in hourly_block:
            result["hourly"] = [item for item in hourly_block["data"]][0:24]

        return result
