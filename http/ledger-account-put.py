#!/usr/bin/env python

from _shared import json_client, print_response

response = json_client.put(
    "/ledger/accounts/1",
    json={
        "uid": 1,
        "name": "account1-updated",
        "opened_on": "1999-01-01",
        "url": "http://updated.example.com"
    }
)

print_response(response)

assert response.status_code == 204
