#!/usr/bin/env python
from _shared import json_client, print_response

response = json_client.post(
    "/speak/notification",
    json={
        "deliveryStyle": "normal",
        "body": "",
        "localId": "test",
        "title": "📦 hello notification 📦",
        "group": "",
        "source": "",
        "url": "http://example.com",
        "publicId": "abcde123",
        "badge": ""
    }
)

print_response(response)

assert response.status_code == 204
