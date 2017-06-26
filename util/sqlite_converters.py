import re
import pytz
import datetime
import pickle
import msgpack

def convert_naive_date(s):
    return datetime.datetime.strptime(s.decode("utf-8"), "%Y-%m-%d %H:%M:%S")

def convert_date(s):
    d = datetime.datetime.strptime(s.decode("utf-8"), "%Y-%m-%d %H:%M:%S")
    return pytz.utc.localize(d)

def convert_duration(s):
    seconds = int(s)
    hours_label = "hour"
    minutes_label = "minute"
    seconds_label = "second"

    hours = seconds // 3600
    seconds -= hours * 3600
    if hours != 1:
        hours_label += "s"

    minutes = seconds // 60
    seconds -= minutes * 60
    if minutes != 1:
        minutes_label += "s"

    if seconds != 1:
        seconds_label += "s"

    result = []
    if hours > 0:
        result.append("{} {}".format(hours, hours_label))

    if minutes > 0:
        result.append("{} {}".format(minutes, minutes_label))

    if seconds > 0:
        result.append("{} {}".format(seconds, seconds_label))

    if len(result) == 0:
        result.append("0 {}".format(seconds_label))

    return ", ".join(result)

def convert_callerid(s):
    return re.sub(r'"(.*?)".*', r"\1", s.decode("utf-8"))

def convert_binary(blob):
    try:
        return msgpack.unpackb(blob, encoding='utf-8')
    except msgpack.exceptions.ExtraData:
        return pickle.loads(blob)


def convert_channel(s):
    decoded_s = s.decode("utf-8")
    return decoded_s[0:decoded_s.rindex("-")]
