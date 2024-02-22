#!/usr/bin/env python

from _shared import json_client, print_response

response = json_client.post(
    "/reminders/",
    data={
        "confirm": 1,
        "minutes": 1,
        "notification_id": "test",
    }
)

print_response(response)

assert response.status_code == 204
