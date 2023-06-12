#!/usr/bin/env python

from _shared import json_client, print_response

response = json_client.post(
    "/ledger/transactions",
    json={
        "occurred_on": "2020-01-01",
        "payee": "transfer test",
        "amount": 666,
        "account_id": 1,
        "destination_id": 5,
        "note": "This is my note",
        "tags": ["transfer"]
    }
)

print_response(response)

assert response.status_code == 204
