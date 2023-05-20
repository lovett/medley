#!/usr/bin/env python

from _shared import json_client, print_response

response = json_client.get("/ledger/transactions/0")

print_response(response)

assert response.status_code == 200
