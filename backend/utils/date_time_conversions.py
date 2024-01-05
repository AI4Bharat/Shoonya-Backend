from datetime import datetime
from dateutil import tz


def utc_to_ist(utc_time):
    from_zone = tz.gettz("UTC")
    to_zone = tz.gettz("Asia/Kolkata")

    utc = utc_time.replace(tzinfo=from_zone)

    central = utc.astimezone(to_zone)
    s = central.strftime("%d-%m-%Y %H:%M:%S")
    return s

def ist_to_utc(ist_time, date_time_format):
    to_zone = tz.gettz("UTC")
    from_zone = tz.gettz("Asia/Kolkata")

    ist = ist_time.replace(tzinfo=from_zone)

    central = ist.astimezone(to_zone)
    s = central.strftime(date_time_format)
    return s
