#!/usr/bin/env python

from _shared import json_client, print_response

response = json_client.post(
    "/ledger/transactions",
    json={
        "occurred_on": "2020-01-01",
        "payee": "My Test Payee",
        "amount": 12345,
        "account_id": 1,
        "notes": "This is my note",
        "tags": ["apple", "banana", "orange"]
    }
)

print_response(response)

assert response.status_code == 204
