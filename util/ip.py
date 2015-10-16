import os.path
import time
import re
import sqlite3
import util.sqlite_converters
import netaddr
import util.fs
import hashlib
import functools
import pickle
import apps.registry.models
import apps.geodb.models

@functools.lru_cache()
def facts(ip, geo_lookup=True):
    registry = apps.registry.models.Registry()
    address = netaddr.IPAddress(ip)
    netblocks = registry.search(key="netblock*")
    facts = {}

    for netblock in netblocks:
        if address in netaddr.IPNetwork(netblock["value"]):
            facts["organization"] = netblock["key"].split(":")[1]
            break

    annotations = registry.search(key="ip:{}".format(ip))
    if annotations:
        facts["annotations"] = [annotation["value"] for annotation in annotations]

    if geo_lookup:
        geodb = apps.geodb.models.GeoDB()

        facts["geo"] = geodb.findByIp(ip)
    else:
        facts["geo"] = {}

    return facts
