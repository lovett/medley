#!/usr/bin/env python

from _shared import json_client, print_response

response = json_client.post(
    "/ledger/accounts",
    json={
        "name": "account1",
        "opened_on": "2020-01-01",
        "closed_on": "2020-09-09",
        "url": "http://example.com"
    }
)

print_response(response)

assert response.status_code == 201
assert response.headers['content-length'] == "0"
assert response.headers['content-location']
