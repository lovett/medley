#!/usr/bin/env python

from _shared import json_client, print_response

response = json_client.get("/ledger/transactions?q=payee:first")

print_response(response)

assert response.status_code == 200
