#!/usr/bin/env python

from _shared import basic_client, print_response

response = basic_client.post(
    "/speak",
    data={
        "action": "toggle"
    }
)

print_response(response)

assert response.status_code == 303
