#!/usr/bin/env python

from _shared import basic_client, print_response

response = basic_client.delete("/sleeplog/1")

print_response(response)

assert response.status_code == 204
